#!/bin/bash
echo "BUILD START"
python3 -m pip install -r requirements.txt
python3 manage.py collectstatic --noinput --verbosity 2
echo "BUILD END"
