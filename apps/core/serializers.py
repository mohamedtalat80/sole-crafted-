import json

from django.http import QueryDict
from rest_framework import serializers


class MultipartJsonListMixin:
    """
    Fixes two multipart/form-data issues for serializers that have ListFields.

    Issue 1 — JSON-encoded list fields:
      Multipart sends available_days/includes as a single JSON string, e.g.
        available_days=[{"day":"monday",...}]
      DRF's ListField.get_value() returns ['[{"day":"monday",...}]'].
      The child serializer receives the raw JSON string, causing AttributeError
      inside StrictSerializer (str has no .keys()) → 500.
      Fix: parse JSON strings into real lists before validation.

    Issue 2 — File fields read from request.FILES, not request.data:
      Swagger/Postman may send the image filename as plain text in form-data.
      The view reads actual files from request.FILES directly and ignores the
      validated value, so excluding these fields from data lets the field's
      default kick in and avoids false "not a file" validation errors.

    Subclasses declare:
      json_list_fields      = ('includes', 'available_days')
      json_dict_fields      = ('metadata', 'specifications')
      multipart_file_fields = ('images',)
    """

    json_list_fields: tuple = ()
    json_dict_fields: tuple = ()
    multipart_file_fields: tuple = ()

    def to_internal_value(self, data):
        if isinstance(data, (QueryDict, dict)):
            is_query_dict = isinstance(data, QueryDict)
            data_dict: dict = {}
            aliasable_fields = (
                *self.json_list_fields,
                *self.json_dict_fields,
                *self.multipart_file_fields,
            )

            # Helper for uniform access to lists of values
            def get_vals(k):
                if is_query_dict:
                    return data.getlist(k)
                v = data_dict.get(k)
                if v is None:
                    return []
                return v if isinstance(v, list) else [v]

            # 1. Normalize into a plain dictionary
            if is_query_dict:
                for key in set(data.keys()):
                    vals = data.getlist(key)
                    data_dict[key] = vals[0] if len(vals) == 1 else vals
            else:
                data_dict = data.copy()

            # 1.5 Normalize common bracket aliases like `images[]` to `images`
            # before strict field validation runs.
            for field in aliasable_fields:
                bracket_key = f"{field}[]"
                if field in data_dict or bracket_key not in data_dict:
                    continue
                data_dict[field] = data_dict.pop(bracket_key)

            # 2. Expand JSON-encoded list fields or plain repeated values
            for field in self.json_list_fields:
                raw = get_vals(field)
                if not raw:
                    continue
                if len(raw) == 1 and isinstance(raw[0], str):
                    try:
                        parsed = json.loads(raw[0])
                        if isinstance(parsed, list):
                            data_dict[field] = parsed
                        elif isinstance(parsed, dict):
                            data_dict[field] = [parsed]
                        else:
                            data_dict[field] = raw
                    except (json.JSONDecodeError, ValueError):
                        data_dict[field] = raw
                else:
                    data_dict[field] = raw

            # 3. Expand JSON-encoded dict fields
            for field in self.json_dict_fields:
                raw = get_vals(field)
                if not raw:
                    continue
                if len(raw) == 1 and isinstance(raw[0], str):
                    try:
                        parsed = json.loads(raw[0])
                        if isinstance(parsed, dict):
                            data_dict[field] = parsed
                        elif isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
                            data_dict[field] = parsed[0]
                        else:
                            data_dict[field] = raw
                    except (json.JSONDecodeError, ValueError):
                        data_dict[field] = raw
                else:
                    data_dict[field] = raw

            # 4. Support structured form-data arrays like `field[0].subfield`
            import re
            list_dicts = {field: {} for field in self.json_list_fields}
            for key in list(data_dict.keys()):
                for field in self.json_list_fields:
                    match = re.match(rf"^{field}\[(\d+)\]\.(.+)$", key)
                    if not match:
                        match = re.match(rf"^{field}\[(\d+)\]\[(.+)\]$", key)
                    if match:
                        index = int(match.group(1))
                        sub_key = match.group(2)
                        if index not in list_dicts[field]:
                            list_dicts[field][index] = {}
                        
                        vals = get_vals(key)
                        list_dicts[field][index][sub_key] = vals[0] if len(vals) == 1 else vals
                        data_dict.pop(key, None)

            for field in self.json_list_fields:
                if list_dicts[field]:
                    sorted_indices = sorted(list_dicts[field].keys())
                    parsed_list = [list_dicts[field][idx] for idx in sorted_indices]
                    # Only override if we actually found indexed fields for this field
                    data_dict[field] = parsed_list

            # 5. Handle file fields
            from django.core.files.uploadedfile import UploadedFile
            for field in self.multipart_file_fields:
                if field in data_dict:
                    raw_vals = get_vals(field)
                    valid_files = [f for f in raw_vals if isinstance(f, UploadedFile)]
                    if valid_files:
                        # Always keep as a list — ListField iterates over its value,
                        # and a bare UploadedFile is iterable (lines), causing false errors.
                        data_dict[field] = valid_files
                    else:
                        # If a file field contains a string (filename), it's usually useless junk from Swagger
                        if not any(isinstance(f, UploadedFile) for f in raw_vals):
                            data_dict.pop(field, None)

            data = data_dict
        return super().to_internal_value(data)



class ChoiceField(serializers.ChoiceField):
    """
    ChoiceField that includes the list of valid choices in the error message.
    """

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError:
            valid = ", ".join(str(k) for k in self.choices.keys())
            raise serializers.ValidationError(
                f'"{data}" is not a valid choice. Valid choices are: {valid}.'
            )


class StrictSerializer(serializers.Serializer):
    """
    Rejects any field not declared on the serializer.

    DRF silently ignores unknown fields by default. Inheriting from this
    class instead of serializers.Serializer causes a 400 ValidationError
    when the client sends unexpected keys.
    """

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                {"non_field_errors": ["Expected a JSON object (dict), got a different type."]}
            )
        declared = set(self.fields.keys())
        unknown = set(data.keys()) - declared
        if unknown:
            raise serializers.ValidationError(
                {field: ["This field is not allowed."] for field in unknown}
            )
        return super().to_internal_value(data)


class StrictModelSerializer(serializers.ModelSerializer):
    """
    ModelSerializer variant that rejects any field not declared on the serializer.

    Use this instead of serializers.ModelSerializer wherever unknown fields
    should be rejected with a 400 rather than silently ignored.
    """

    serializer_choice_field = ChoiceField

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                {"non_field_errors": ["Expected a JSON object (dict), got a different type."]}
            )
        declared = set(self.fields.keys())
        unknown = set(data.keys()) - declared
        if unknown:
            raise serializers.ValidationError(
                {field: ["This field is not allowed."] for field in unknown}
            )
        return super().to_internal_value(data)
