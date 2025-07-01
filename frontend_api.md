 API Documentation

This document provides a comprehensive overview of all API endpoints used in the Maritime Artisans Export project.

## API Configuration

- *Base URL*: http://localhost:3001/api (configurable via VITE_API_URL environment variable)
- *Authentication*: Authentication is handled via a Bearer token sent in the Authorization header. The token is retrieved from localStorage and automatically added to requests by an Axios interceptor.
- *Error Handling*: An Axios response interceptor handles API errors. If a 401 Unauthorized status is received, the user's authentication token and data are cleared from localStorage, and the application redirects to the /login page.
- *File Location*: src/services/api.ts

## Endpoints Summary

| Method     | Endpoint                                 | Description                  | Module |
| ---------- | ---------------------------------------- | ---------------------------- | ------ |
| *GET*    | /products                              | Get all products             | Public |
| *GET*    | /products/:id                          | Get a single product         | Public |
| *GET*    | /products/categories                   | Get product categories       | Public |
| *GET*    | /services                              | Get all services             | Public |
| *GET*    | /services/:id                          | Get a single service         | Public |
| *GET*    | /gallery                               | Get gallery items            | Public |
| *GET*    | /gallery/categories                    | Get gallery categories       | Public |
| *GET*    | /blog                                  | Get blog posts               | Public |
| *GET*    | /blog/:id                              | Get a single blog post       | Public |
| *GET*    | /blog/categories                       | Get blog categories          | Public |
| *POST*   | /contact                               | Submit contact form          | Public |
| *GET*    | /contact/info                          | Get contact information      | Public |
| *GET*    | /about                                 | Get about company info       | Public |
| *GET*    | /company/stats                         | Get company statistics       | Public |
| *POST*   | /admin/auth/login                      | Login as admin               | Admin  |
| *POST*   | /admin/auth/logout                     | Logout as admin              | Admin  |
| *POST*   | /admin/auth/refresh                    | Refresh admin auth token     | Admin  |
| *GET*    | /admin/auth/profile                    | Get admin profile            | Admin  |
| *GET*    | /admin/products                        | Get all products (admin)     | Admin  |
| *GET*    | /admin/products/:id                    | Get a single product (admin) | Admin  |
| *POST*   | /admin/products                        | Create a new product         | Admin  |
| *PUT*    | /admin/products/:id                    | Update a product             | Admin  |
| *DELETE* | /admin/products/:id                    | Delete a product             | Admin  |
| *POST*   | /admin/products/:id/image              | Upload product image         | Admin  |
| *GET*    | /admin/orders                          | Get all orders               | Admin  |
| *GET*    | /admin/orders/:id                      | Get a single order           | Admin  |
| *POST*   | /admin/orders                          | Create a new order           | Admin  |
| *PUT*    | /admin/orders/:id                      | Update an order              | Admin  |
| *DELETE* | /admin/orders/:id                      | Delete an order              | Admin  |
| *PATCH*  | /admin/orders/:id/status               | Update order status          | Admin  |
| *GET*    | /admin/customers                       | Get all customers            | Admin  |
| *GET*    | /admin/customers/:id                   | Get a single customer        | Admin  |
| *POST*   | /admin/customers                       | Create a new customer        | Admin  |
| *PUT*    | /admin/customers/:id                   | Update a customer            | Admin  |
| *DELETE* | /admin/customers/:id                   | Delete a customer            | Admin  |
| *GET*    | /admin/analytics/sales                 | Get sales analytics          | Admin  |
| *GET*    | /admin/analytics/orders                | Get order analytics          | Admin  |
| *GET*    | /admin/analytics/customers             | Get customer analytics       | Admin  |
| *GET*    | /admin/analytics/revenue               | Get revenue report           | Admin  |
| *GET*    | /admin/analytics/exports               | Get export report            | Admin  |
| *GET*    | /admin/inventory                       | Get inventory items          | Admin  |
| *GET*    | /admin/inventory/:id                   | Get a single inventory item  | Admin  |
| *PUT*    | /admin/inventory/:id                   | Update inventory item        | Admin  |
| *POST*   | /admin/inventory/:id/alerts            | Set low stock alert          | Admin  |
| *GET*    | /admin/shipments                       | Get all shipments            | Admin  |
| *GET*    | /admin/shipments/:id                   | Get a single shipment        | Admin  |
| *POST*   | /admin/shipments                       | Create a new shipment        | Admin  |
| *PUT*    | /admin/shipments/:id                   | Update a shipment            | Admin  |
| *GET*    | /admin/shipments/track/:trackingNumber | Track a shipment             | Admin  |
| *GET*    | /admin/blog                            | Get all blog posts (admin)   | Admin  |
| *POST*   | /admin/blog                            | Create a new blog post       | Admin  |
| *PUT*    | /admin/blog/:id                        | Update a blog post           | Admin  |
| *DELETE* | /admin/blog/:id                        | Delete a blog post           | Admin  |
| *GET*    | /admin/settings                        | Get settings                 | Admin  |
| *PUT*    | /admin/settings                        | Update settings              | Admin  |
| *GET*    | /admin/company                         | Get company info             | Admin  |
| *PUT*    | /admin/company                         | Update company info          | Admin  |
| *GET*    | /admin/notifications                   | Get notifications            | Admin  |
| *PATCH*  | /admin/notifications/:id/read          | Mark notification as read    | Admin  |
| *DELETE* | /admin/notifications/:id               | Delete a notification        | Admin  |

*Total API Calls Found*: 63

---

## Public APIs

These endpoints are for the public-facing website.

### Get All Products

- *Method*: GET
- *Endpoint*: /products
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:46
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Array of product objects.
- *Notes*: None

### Get Single Product

- *Method*: GET
- *Endpoint*: /products/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:47
- *Request Body*: None
- *Expected Response*: JSON - A single product object.
- *Notes*: id is a string.

### Get Product Categories

- *Method*: GET
- *Endpoint*: /products/categories
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:48
- *Request Body*: None
- *Expected Response*: JSON - Array of category objects/strings.
- *Notes*: None

### Get All Services

- *Method*: GET
- *Endpoint*: /services
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:51
- *Request Body*: None
- *Expected Response*: JSON - Array of service objects.
- *Notes*: None

### Get Single Service

- *Method*: GET
- *Endpoint*: /services/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:52
- *Request Body*: None
- *Expected Response*: JSON - A single service object.
- *Notes*: id is a string.

### Get Gallery

- *Method*: GET
- *Endpoint*: /gallery
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:55
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Array of gallery item objects.
- *Notes*: None

### Get Gallery Categories

- *Method*: GET
- *Endpoint*: /gallery/categories
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:56
- *Request Body*: None
- *Expected Response*: JSON - Array of category objects/strings.
- *Notes*: None

### Get Blog Posts

- *Method*: GET
- *Endpoint*: /blog
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:59
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Array of blog post objects.
- *Notes*: None

### Get Single Blog Post

- *Method*: GET
- *Endpoint*: /blog/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:60
- *Request Body*: None
- *Expected Response*: JSON - A single blog post object.
- *Notes*: id is a string.

### Get Blog Categories

- *Method*: GET
- *Endpoint*: /blog/categories
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:61
- *Request Body*: None
- *Expected Response*: JSON - Array of category objects/strings.
- *Notes*: None

### Submit Contact Form

- *Method*: POST
- *Endpoint*: /contact
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:64
- *Request Body*:

json
{
  "name": "string",
  "email": "string",
  "message": "string"
}


- *Expected Response*: JSON - Confirmation message.
- *Notes*: None

### Get Contact Info

- *Method*: GET
- *Endpoint*: /contact/info
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:65
- *Request Body*: None
- *Expected Response*: JSON - Object containing contact information (e.g., address, phone, email).
- *Notes*: None

### Get About Info

- *Method*: GET
- *Endpoint*: /about
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:68
- *Request Body*: None
- *Expected Response*: JSON - Object containing company's "about" information.
- *Notes*: None

### Get Company Stats

- *Method*: GET
- *Endpoint*: /company/stats
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:69
- *Request Body*: None
- *Expected Response*: JSON - Object containing company statistics.
- *Notes*: None

---

## Admin APIs

These endpoints are for the admin dashboard and require authentication.

### Admin Login

- *Method*: POST
- *Endpoint*: /admin/auth/login
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:75
- *Request Body*:

json
{
  "email": "string",
  "password": "string"
}


- *Expected Response*: JSON - Auth token and user data.
- *Notes*: Publicly accessible, but for admin use.

### Admin Logout

- *Method*: POST
- *Endpoint*: /admin/auth/logout
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:77
- *Request Body*: None
- *Expected Response*: JSON - Confirmation message.
- *Notes*: Requires authentication.

### Refresh Token

- *Method*: POST
- *Endpoint*: /admin/auth/refresh
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:78
- *Request Body*: None
- *Expected Response*: JSON - New auth token.
- *Notes*: Requires authentication.

### Get Admin Profile

- *Method*: GET
- *Endpoint*: /admin/auth/profile
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:79
- *Request Body*: None
- *Expected Response*: JSON - Admin user profile data.
- *Notes*: Requires authentication.

### Get All Products (Admin)

- *Method*: GET
- *Endpoint*: /admin/products
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:82
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Array of product objects.
- *Notes*: Requires authentication.

### Get Single Product (Admin)

- *Method*: GET
- *Endpoint*: /admin/products/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:83
- *Request Body*: None
- *Expected Response*: JSON - A single product object.
- *Notes*: id is a string. Requires authentication.

### Create Product

- *Method*: POST
- *Endpoint*: /admin/products
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:84
- *Request Body*: JSON - Product data.
- *Expected Response*: JSON - The newly created product object.
- *Notes*: Requires authentication.

### Update Product

- *Method*: PUT
- *Endpoint*: /admin/products/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:85
- *Request Body*: JSON - Product data to update.
- *Expected Response*: JSON - The updated product object.
- *Notes*: id is a string. Requires authentication.

### Delete Product

- *Method*: DELETE
- *Endpoint*: /admin/products/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:87
- *Request Body*: None
- *Expected Response*: JSON - Confirmation message.
- *Notes*: id is a string. Requires authentication.

### Upload Product Image

- *Method*: POST
- *Endpoint*: /admin/products/:id/image
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:88
- *Request Body*: multipart/form-data containing the image file.
- *Expected Response*: JSON - Updated product object with new image URL.
- *Notes*: id is a string. Requires authentication.

### Get All Orders

- *Method*: GET
- *Endpoint*: /admin/orders
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:98
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Array of order objects.
- *Notes*: Requires authentication.

### Get Single Order

- *Method*: GET
- *Endpoint*: /admin/orders/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:99
- *Request Body*: None
- *Expected Response*: JSON - A single order object.
- *Notes*: id is a string. Requires authentication.

### Create Order

- *Method*: POST
- *Endpoint*: /admin/orders
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:100
- *Request Body*: JSON - Order data.
- *Expected Response*: JSON - The newly created order object.
- *Notes*: Requires authentication.

### Update Order

- *Method*: PUT
- *Endpoint*: /admin/orders/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:101
- *Request Body*: JSON - Order data to update.
- *Expected Response*: JSON - The updated order object.
- *Notes*: id is a string. Requires authentication.

### Delete Order

- *Method*: DELETE
- *Endpoint*: /admin/orders/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:102
- *Request Body*: None
- *Expected Response*: JSON - Confirmation message.
- *Notes*: id is a string. Requires authentication.

### Update Order Status

- *Method*: PATCH
- *Endpoint*: /admin/orders/:id/status
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:103
- *Request Body*:

json
{
  "status": "string"
}


- *Expected Response*: JSON - The updated order object.
- *Notes*: id is a string. Requires authentication.

### Get All Customers

- *Method*: GET
- *Endpoint*: /admin/customers
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:107
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Array of customer objects.
- *Notes*: Requires authentication.

### Get Single Customer

- *Method*: GET
- *Endpoint*: /admin/customers/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:108
- *Request Body*: None
- *Expected Response*: JSON - A single customer object.
- *Notes*: id is a string. Requires authentication.

### Create Customer

- *Method*: POST
- *Endpoint*: /admin/customers
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:109
- *Request Body*: JSON - Customer data.
- *Expected Response*: JSON - The newly created customer object.
- *Notes*: Requires authentication.

### Update Customer

- *Method*: PUT
- *Endpoint*: /admin/customers/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:111
- *Request Body*: JSON - Customer data to update.
- *Expected Response*: JSON - The updated customer object.
- *Notes*: id is a string. Requires authentication.

### Delete Customer

- *Method*: DELETE
- *Endpoint*: /admin/customers/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:113
- *Request Body*: None
- *Expected Response*: JSON - Confirmation message.
- *Notes*: id is a string. Requires authentication.

### Get Sales Analytics

- *Method*: GET
- *Endpoint*: /admin/analytics/sales
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:117
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Sales analytics data.
- *Notes*: Requires authentication.

### Get Order Analytics

- *Method*: GET
- *Endpoint*: /admin/analytics/orders
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:119
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Order analytics data.
- *Notes*: Requires authentication.

### Get Customer Analytics

- *Method*: GET
- *Endpoint*: /admin/analytics/customers
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:121
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Customer analytics data.
- *Notes*: Requires authentication.

### Get Revenue Report

- *Method*: GET
- *Endpoint*: /admin/analytics/revenue
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:123
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Revenue report data.
- *Notes*: Requires authentication.

### Get Export Report

- *Method*: GET
- *Endpoint*: /admin/analytics/exports
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:125
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Export report data.
- *Notes*: Requires authentication.

### Get Inventory

- *Method*: GET
- *Endpoint*: /admin/inventory
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:129
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Array of inventory items.
- *Notes*: Requires authentication.

### Get Single Inventory Item

- *Method*: GET
- *Endpoint*: /admin/inventory/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:130
- *Request Body*: None
- *Expected Response*: JSON - A single inventory item object.
- *Notes*: id is a string. Requires authentication.

### Update Inventory

- *Method*: PUT
- *Endpoint*: /admin/inventory/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:131
- *Request Body*: JSON - Inventory data to update.
- *Expected Response*: JSON - The updated inventory item object.
- *Notes*: id is a string. Requires authentication.

### Set Low Stock Alert

- *Method*: POST
- *Endpoint*: /admin/inventory/:id/alerts
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:133
- *Request Body*:

json
{
  "threshold": "number"
}


- *Expected Response*: JSON - Confirmation message.
- *Notes*: id is a string. Requires authentication.

### Get All Shipments

- *Method*: GET
- *Endpoint*: /admin/shipments
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:137
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Array of shipment objects.
- *Notes*: Requires authentication.

### Get Single Shipment

- *Method*: GET
- *Endpoint*: /admin/shipments/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:138
- *Request Body*: None
- *Expected Response*: JSON - A single shipment object.
- *Notes*: id is a string. Requires authentication.

### Create Shipment

- *Method*: POST
- *Endpoint*: /admin/shipments
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:139
- *Request Body*: JSON - Shipment data.
- *Expected Response*: JSON - The newly created shipment object.
- *Notes*: Requires authentication.

### Update Shipment

- *Method*: PUT
- *Endpoint*: /admin/shipments/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:141
- *Request Body*: JSON - Shipment data to update.
- *Expected Response*: JSON - The updated shipment object.
- *Notes*: id is a string. Requires authentication.

### Track Shipment

- *Method*: GET
- *Endpoint*: /admin/shipments/track/:trackingNumber
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:143
- *Request Body*: None
- *Expected Response*: JSON - Shipment tracking information.
- *Notes*: trackingNumber is a string. Requires authentication.

### Get All Blog Posts (Admin)

- *Method*: GET
- *Endpoint*: /admin/blog
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:147
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Array of blog post objects.
- *Notes*: Requires authentication.

### Create Blog Post

- *Method*: POST
- *Endpoint*: /admin/blog
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:148
- *Request Body*: JSON - Blog post data.
- *Expected Response*: JSON - The newly created blog post object.
- *Notes*: Requires authentication.

### Update Blog Post

- *Method*: PUT
- *Endpoint*: /admin/blog/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:149
- *Request Body*: JSON - Blog post data to update.
- *Expected Response*: JSON - The updated blog post object.
- *Notes*: id is a string. Requires authentication.

### Delete Blog Post

- *Method*: DELETE
- *Endpoint*: /admin/blog/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:150
- *Request Body*: None
- *Expected Response*: JSON - Confirmation message.
- *Notes*: id is a string. Requires authentication.

### Get Settings

- *Method*: GET
- *Endpoint*: /admin/settings
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:153
- *Request Body*: None
- *Expected Response*: JSON - Settings object.
- *Notes*: Requires authentication.

### Update Settings

- *Method*: PUT
- *Endpoint*: /admin/settings
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:154
- *Request Body*: JSON - Settings data to update.
- *Expected Response*: JSON - The updated settings object.
- *Notes*: Requires authentication.

### Get Company Info

- *Method*: GET
- *Endpoint*: /admin/company
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:155
- *Request Body*: None
- *Expected Response*: JSON - Company info object.
- *Notes*: Requires authentication.

### Update Company Info

- *Method*: PUT
- *Endpoint*: /admin/company
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:156
- *Request Body*: JSON - Company info data to update.
- *Expected Response*: JSON - The updated company info object.
- *Notes*: Requires authentication.

### Get Notifications

- *Method*: GET
- *Endpoint*: /admin/notifications
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:160
- *Request Body*: None (Accepts optional query params)
- *Expected Response*: JSON - Array of notification objects.
- *Notes*: Requires authentication.

### Mark Notification as Read

- *Method*: PATCH
- *Endpoint*: /admin/notifications/:id/read
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:162
- *Request Body*: None
- *Expected Response*: JSON - Confirmation message.
- *Notes*: id is a string. Requires authentication.

### Delete Notification

- *Method*: DELETE
- *Endpoint*: /admin/notifications/:id
- *Status*: 🔴 Not Implemented (Backend endpoint needed)
- *File Location*: src/services/api.ts:164
- *Request Body*: None
- *Expected Response*: JSON - Confirmation message.
- *Notes*: id is a string. Requires authentication.