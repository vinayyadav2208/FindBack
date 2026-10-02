# FindBack
## AI-Powered Lost, Found, Donation & Community Recovery Platform

Version: 1.0  
Project Type: Full-Stack AI Web Application  
Status: Active Development

---

# 1. IMPORTANT INSTRUCTIONS FOR OPENCODE

You are the primary coding agent responsible for developing the FindBack application.

Before writing or modifying code:

1. Read this entire MASTER_README.md.
2. Inspect the existing project structure.
3. Inspect the existing backend code.
4. Inspect the existing frontend code, if present.
5. Inspect the existing database configuration.
6. Inspect existing database models and tables.
7. Preserve working functionality.
8. Do not rebuild working features unnecessarily.
9. Do not delete existing functionality unless explicitly required.
10. Implement features incrementally.
11. Test every major feature after implementation.
12. Fix errors before moving to the next phase.
13. Keep the application runnable after every phase.
14. Update the project progress section after completing a phase.
15. If an architectural decision is necessary, choose a maintainable solution and document it.

The existing project may already contain partially implemented functionality.

**DO NOT assume this is a blank project.**

The existing implementation is the source of truth for what has already been completed.

---

# 2. PROJECT VISION

FindBack is a community-driven platform designed to help people:

- Find lost belongings
- Return found belongings
- Give away unwanted usable items
- Discover nearby listings
- Automatically identify potential lost/found matches using AI
- Verify ownership before returning valuable items
- Receive notifications about relevant matches
- Report suspicious or fraudulent listings

The application combines:

- Community reporting
- Search
- Location
- Authentication
- AI text matching
- AI image matching
- Notifications
- Ownership verification
- Moderation

The long-term goal is to make finding lost belongings significantly easier while maintaining privacy and preventing fraudulent claims.

---

# 3. CORE USER JOURNEY

The primary user journey is:

```text
User registers
      ↓
User logs in
      ↓
User reports lost item
      ↓
System stores item
      ↓
AI generates searchable representation
      ↓
System searches found items
      ↓
Potential matches identified
      ↓
User receives notification
      ↓
User opens potential match
      ↓
User submits ownership claim
      ↓
Verification process
      ↓
Found-item owner reviews claim
      ↓
Item returned
      ↓
Listing marked resolved
```

The reverse flow should also work:

```text
User finds item
      ↓
Reports found item
      ↓
AI analyzes listing
      ↓
System searches lost reports
      ↓
Potential matches identified
      ↓
Lost-item owner notified
      ↓
Ownership verification
      ↓
Item returned
```

---

# 4. TECHNOLOGY STACK

## Frontend

Use:

- React
- TypeScript
- Vite
- React Router
- Tailwind CSS
- Axios
- Lucide React

Optional supporting libraries:

- React Hook Form
- Zod
- TanStack Query
- Recharts
- date-fns

Do not introduce large dependencies without a reason.

---

# 5. BACKEND

Use:

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- PyMySQL
- JWT authentication
- Passlib/bcrypt

AI services:

- Sentence Transformers
- Gemini API
- FAISS
- CLIP

Backend should follow a modular architecture.

---

# 6. DATABASE

Use:

```text
MySQL 8+
```

Development database:

```text
findback
```

Database configuration must use environment variables.

Never hardcode:

- password
- database credentials
- JWT secret
- Gemini API key
- cloud storage credentials

---

# 7. RECOMMENDED PROJECT STRUCTURE

Final architecture:

```text
findback/
│
├── backend/
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── security.py
│   │   ├── dependencies.py
│   │   │
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── lost_items.py
│   │   │   ├── found_items.py
│   │   │   ├── donations.py
│   │   │   ├── matches.py
│   │   │   ├── claims.py
│   │   │   ├── notifications.py
│   │   │   ├── reports.py
│   │   │   └── admin.py
│   │   │
│   │   ├── services/
│   │   │   ├── matching_service.py
│   │   │   ├── embedding_service.py
│   │   │   ├── image_service.py
│   │   │   ├── notification_service.py
│   │   │   └── verification_service.py
│   │   │
│   │   ├── utils/
│   │   │   ├── validators.py
│   │   │   └── helpers.py
│   │   │
│   │   └── tests/
│   │
│   ├── create_tables.py
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
│
├── frontend/
│   │
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── contexts/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── ai/
│   ├── embeddings/
│   ├── matching/
│   ├── image_matching/
│   └── evaluation/
│
├── docs/
├── .gitignore
├── MASTER_README.md
└── README.md
```

If the current project structure differs, do not immediately restructure everything.

First determine whether the existing structure can be extended safely.

---

# 8. CURRENT IMPLEMENTATION

The existing implementation already contains the foundation of FindBack.

Current backend:

```text
app/
├── __init__.py
├── database.py
├── main.py
├── models.py
├── schemas.py
└── security.py

create_tables.py
```

Current database:

```text
findback
├── users
├── lost_items
└── found_items
```

Already implemented:

```text
FastAPI
MySQL connection
SQLAlchemy
User model
LostItem model
FoundItem model
User registration
Password hashing
JWT login
JWT authentication
GET /me
Lost item creation
Lost item listing
My lost items
Found item schema
Found item model
Found item creation
```

Continue from this implementation.

Do not throw away the existing backend.

---

# 9. AUTHENTICATION

Authentication must use JWT.

Flow:

```text
Register
   ↓
Hash password
   ↓
Store user
   ↓
Login
   ↓
Verify password
   ↓
Generate JWT
   ↓
Frontend stores token
   ↓
Protected API
   ↓
Backend validates JWT
```

JWT must contain at minimum:

```text
user_id
email
expiration
```

JWT should expire.

Do not create permanent tokens.

---

# 10. PASSWORD SECURITY

Passwords must NEVER be stored as plaintext.

Use:

```text
bcrypt
```

Password requirements should eventually include:

- minimum length
- reasonable complexity
- validation

Do not expose password hashes through APIs.

---

# 11. USER MODEL

User:

```text
users
```

Fields:

```text
id
name
email
password
role
created_at
updated_at
```

Roles:

```text
USER
ADMIN
```

Email must be unique.

---

# 12. LOST ITEM MODEL

Table:

```text
lost_items
```

Fields:

```text
id
name
description
category
location
latitude
longitude
status
user_id
created_at
updated_at
```

Statuses:

```text
ACTIVE
MATCHED
CLAIMED
RESOLVED
CANCELLED
```

Relationships:

```text
User
  ↓
LostItem
```

---

# 13. FOUND ITEM MODEL

Table:

```text
found_items
```

Fields:

```text
id
name
description
category
location
latitude
longitude
status
user_id
created_at
updated_at
```

Statuses:

```text
ACTIVE
MATCHED
CLAIMED
RETURNED
CANCELLED
```

---

# 14. IMPORTANT OWNERSHIP RULE

The frontend must NEVER be allowed to choose the owner.

Never accept:

```json
{
  "user_id": 50
}
```

from the frontend when creating an item.

Instead:

```text
JWT
 ↓
current_user
 ↓
current_user.id
 ↓
database user_id
```

This applies to:

- lost items
- found items
- donations
- claims
- reports

---

# 15. ITEM CATEGORIES

Use:

```text
Electronics
Wallet
Bag
Keys
Documents
Jewelry
Clothing
Watch
Phone
Laptop
Tablet
Books
Accessories
Other
```

Categories should be extensible.

---

# 16. ITEM IMAGES

Users should be able to upload images.

Requirements:

- Validate file type
- Validate file size
- Reject executable files
- Generate safe filenames
- Store only approved formats
- Do not expose local filesystem paths
- Store image URL/path in database

Supported:

```text
JPEG
PNG
WEBP
```

Do not store huge images directly inside MySQL.

Prefer object storage or a dedicated media service.

---

# 17. LOST ITEM API

Required:

```http
POST /lost-items
GET /lost-items
GET /lost-items/{id}
GET /my-lost-items
PUT /lost-items/{id}
DELETE /lost-items/{id}
```

Creation:

```json
{
  "name": "Black Wallet",
  "description": "Black leather wallet",
  "category": "Wallet",
  "location": "JNTU Metro"
}
```

Owner automatically comes from JWT.

---

# 18. FOUND ITEM API

Required:

```http
POST /found-items
GET /found-items
GET /found-items/{id}
GET /my-found-items
PUT /found-items/{id}
DELETE /found-items/{id}
```

Creation:

```json
{
  "name": "Black Wallet",
  "description": "Found black leather wallet",
  "category": "Wallet",
  "location": "JNTU Metro"
}
```

Owner automatically comes from JWT.

---

# 19. SEARCH

Implement global search.

Search fields:

```text
name
description
location
category
```

Example:

```text
GET /search?q=black wallet
```

Search results should combine:

```text
Lost
Found
Donation
```

Provide filtering.

---

# 20. FILTERING

Filters:

```text
type
category
location
date
status
distance
```

Example:

```text
/lost-items?category=Wallet&location=Hyderabad
```

Filtering must be done efficiently at database level where possible.

---

# 21. LOCATION

Items should support location information.

Store:

```text
location
latitude
longitude
```

Do not publicly expose overly precise private locations.

For privacy-sensitive listings, display approximate locations.

Example:

Instead of:

```text
House 43, Street 7
```

show:

```text
KPHB, Hyderabad
```

---

# 22. NEARBY ITEMS

Implement:

```text
GET /nearby
```

Users should be able to find nearby:

- lost items
- found items
- donations

Use geographic distance calculations.

Initial implementation can use MySQL geographic calculations.

Keep this logic modular.

---

# 23. DONATIONS

FindBack also acts as a free-giveaway platform.

Users can list items they want to give away.

Donation fields:

```text
id
name
description
category
condition
location
latitude
longitude
images
status
user_id
created_at
```

Condition:

```text
NEW
LIKE_NEW
GOOD
FAIR
```

Status:

```text
AVAILABLE
RESERVED
CLAIMED
CANCELLED
```

---

# 24. DONATION APIs

Implement:

```http
POST /donations
GET /donations
GET /donations/{id}
GET /my-donations
PUT /donations/{id}
DELETE /donations/{id}
POST /donations/{id}/claim
```

---

# 25. CLAIM SYSTEM

Claims are important.

A user should be able to claim:

- found items
- donations

Create:

```text
claims
```

Fields:

```text
id
item_type
item_id
claimant_id
message
status
created_at
updated_at
```

Status:

```text
PENDING
APPROVED
REJECTED
CANCELLED
```

---

# 26. OWNERSHIP VERIFICATION

For lost/found items, a claim should not automatically transfer ownership.

Potential verification questions:

```text
What color is the item?
What distinctive mark does it have?
What was inside?
What brand was it?
Approximately when was it lost?
Where was it lost?
```

Some verification information may be hidden from public listings.

The finder can review the claim.

The system can assist with AI-generated verification suggestions.

AI must NOT make the final ownership decision.

---

# 27. AI MATCHING

AI matching is a core FindBack feature.

The system should compare:

```text
Lost item
vs
Found items
```

and:

```text
Found item
vs
Lost items
```

---

# 28. TEXT EMBEDDINGS

Use Sentence Transformers.

Recommended initial model:

```text
all-MiniLM-L6-v2
```

Build text:

```text
name
+
description
+
category
+
location
```

Generate embedding.

Store or index embedding in vector storage.

---

# 29. VECTOR SEARCH

Initial implementation:

```text
FAISS
```

Architecture:

```text
MySQL
  |
  | item metadata
  |
Embedding Service
  |
  ↓
FAISS
  |
  ↓
Similarity Search
  |
  ↓
Potential Matches
```

The vector layer must be abstracted behind a service.

Do not tightly couple the entire application to FAISS.

---

# 30. MATCH MODEL

Create:

```text
matches
```

Fields:

```text
id
lost_item_id
found_item_id
text_score
image_score
location_score
category_score
combined_score
status
created_at
```

Status:

```text
POTENTIAL
VIEWED
CONTACTED
VERIFIED
REJECTED
RESOLVED
```

---

# 31. MATCHING ALGORITHM

Initial scoring:

```text
text similarity
+
location similarity
+
category similarity
+
image similarity
```

Example conceptual formula:

```text
combined_score =
    text_score * 0.50
  + image_score * 0.30
  + location_score * 0.15
  + category_score * 0.05
```

These weights are configurable.

Do not treat the score as proof.

Use it only to rank potential matches.

---

# 32. IMAGE MATCHING

Use CLIP or an equivalent image embedding model.

Pipeline:

```text
Image
 ↓
CLIP
 ↓
Embedding
 ↓
Vector search
 ↓
Similarity
```

Combine text and image evidence.

---

# 33. GEMINI

Gemini can assist with:

- Description normalization
- Item classification
- Search query understanding
- Match explanation
- Verification question generation
- Future AI assistant

Never expose the API key in frontend code.

All Gemini calls should happen through the backend.

---

# 34. AI MATCH EXPLANATION

When a potential match is found, show:

```text
Potential Match

Why this may match:

✓ Similar item type
✓ Similar color
✓ Similar location
✓ Similar description

AI confidence:
Potential match
```

Avoid saying:

```text
This is definitely your item.
```

AI should not make definitive ownership claims.

---

# 35. NOTIFICATIONS

Create:

```text
notifications
```

Fields:

```text
id
user_id
type
title
message
is_read
created_at
```

Types:

```text
MATCH_FOUND
CLAIM_RECEIVED
CLAIM_APPROVED
CLAIM_REJECTED
LISTING_REPORTED
DONATION_CLAIMED
SYSTEM
```

---

# 36. NOTIFICATION APIs

Implement:

```http
GET /notifications
PUT /notifications/{id}/read
PUT /notifications/read-all
```

Frontend should show unread count.

Example:

```text
🔔 3
```

---

# 37. REAL-TIME NOTIFICATIONS

Initial version:

```text
REST API
```

Later support:

```text
WebSocket
```

Do not add WebSockets unless necessary.

Keep notification service modular.

---

# 38. REPORTING SYSTEM

Users can report:

- fake listings
- scams
- inappropriate content
- duplicate listings
- suspicious behavior

Create:

```text
reports
```

Fields:

```text
id
reporter_id
target_type
target_id
reason
description
status
created_at
```

Status:

```text
OPEN
UNDER_REVIEW
RESOLVED
DISMISSED
```

---

# 39. ADMIN SYSTEM

Admin dashboard.

Admin capabilities:

```text
View users
View listings
View reports
Review claims
Remove listings
Suspend accounts
Review suspicious activity
View system statistics
```

Admin APIs must be protected by role.

Normal users must not access admin endpoints.

---

# 40. DASHBOARD

User dashboard:

```text
Welcome, <username>

Lost Items          5
Found Items         3
Potential Matches   2
Donations           4
Notifications       3
```

Quick actions:

```text
Report Lost Item
Report Found Item
Donate Item
View Matches
```

---

# 41. FRONTEND ROUTES

Implement:

```text
/
 /login
 /register
 /dashboard
 /lost-items
 /lost-items/:id
 /found-items
 /found-items/:id
 /donations
 /donations/:id
 /report-lost
 /report-found
 /donate
 /matches
 /notifications
 /my-listings
 /profile
 /admin
```

---

# 42. HOME PAGE

Hero:

```text
Find what you've lost.
Return what you've found.
Give what you no longer need.
```

Buttons:

```text
Report Lost Item
Report Found Item
Browse Items
Donate an Item
```

Sections:

```text
Hero
Search
Statistics
Recent Lost Items
Recent Found Items
Donations
How FindBack Works
AI Matching
Safety
Call to Action
Footer
```

---

# 43. NAVBAR

Desktop:

```text
FindBack

Home
Lost
Found
Donations
Search

Login
Register
```

Authenticated:

```text
Dashboard
My Listings
Matches
Notifications
Profile
Logout
```

Mobile:

Use responsive menu.

---

# 44. ITEM CARD

Every listing card should contain:

```text
Image
Name
Category
Short description
Location
Date
Status
```

Button:

```text
View Details
```

Avoid exposing unnecessary personal information.

---

# 45. ITEM DETAILS

Show:

```text
Images
Name
Category
Description
Location
Date
Status
Reporter
```

Actions:

Lost item:

```text
I Found This
Report
```

Found item:

```text
This Is Mine
Claim
Report
```

Donation:

```text
Request Item
Report
```

---

# 46. AUTHENTICATED FRONTEND

Create an authentication context.

Store:

```text
JWT
Current user
Authentication status
```

Protected routes:

```text
/dashboard
/report-lost
/report-found
/donate
/matches
/notifications
/profile
```

Unauthenticated users should be redirected to login where appropriate.

---

# 47. API CLIENT

Use Axios.

Create a centralized API client.

Example:

```text
src/services/api.ts
```

The client should:

- set base URL
- attach JWT
- handle 401
- provide reusable API methods

Do not duplicate Axios configuration throughout components.

---

# 48. FRONTEND STATE

Prefer:

```text
React Context
+
TanStack Query
```

or another lightweight predictable solution.

Avoid unnecessary global state.

---

# 49. FORMS

Use:

```text
React Hook Form
```

where useful.

Validate:

```text
Required fields
Email
Password
Description length
Image type
Image size
```

Show clear validation messages.

---

# 50. ERROR HANDLING

Handle:

```text
400
401
403
404
409
422
429
500
```

Show user-friendly messages.

Never display stack traces.

---

# 51. LOADING STATES

Every network operation should provide feedback.

Examples:

```text
Loading...
Submitting...
Uploading...
Searching...
Finding matches...
Processing image...
```

Disable buttons during submission.

---

# 52. EMPTY STATES

Example:

```text
No lost items found.

Try another search or location.
```

Personal:

```text
You haven't reported any lost items yet.

[Report Lost Item]
```

---

# 53. RESPONSIVE DESIGN

Support:

```text
Desktop
Laptop
Tablet
Mobile
```

Use responsive Tailwind classes.

Do not design only for desktop.

---

# 54. ACCESSIBILITY

Use:

- semantic HTML
- accessible buttons
- labels
- keyboard navigation
- sufficient contrast
- alt text
- focus states

Images must have meaningful alt text.

---

# 55. SECURITY

Required:

```text
Password hashing
JWT expiration
Authorization
Role-based authorization
Input validation
SQLAlchemy ORM
CORS configuration
File validation
Rate limiting where appropriate
Environment variables
```

Never:

```text
Store plaintext passwords
Hardcode API keys
Hardcode DB passwords
Expose JWT secret
Trust user_id from frontend
Expose private verification data
```

---

# 56. ENVIRONMENT VARIABLES

Create:

```text
.env.example
```

Example:

```env
DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost:3306/findback

SECRET_KEY=replace-with-secure-secret

GEMINI_API_KEY=replace-with-key

FRONTEND_URL=http://localhost:5173
```

Never commit `.env`.

---

# 57. DATABASE MIGRATIONS

For the initial development version, table creation may use:

```text
create_tables.py
```

As the application grows, migrate to:

```text
Alembic
```

Do not destroy existing tables to apply schema changes.

Use proper migrations.

---

# 58. API DOCUMENTATION

FastAPI Swagger should remain enabled in development.

Expected:

```text
/docs
```

Also support:

```text
/redoc
```

Document endpoints using:

- summary
- description
- request schema
- response schema
- status codes

---

# 59. API RESPONSE FORMAT

Keep API responses consistent.

Success:

```json
{
  "message": "Operation successful",
  "data": {}
}
```

For lists:

```json
{
  "items": [],
  "total": 0
}
```

Errors:

```json
{
  "detail": "Human-readable error message"
}
```

Do not leak internal exceptions.

---

# 60. HTTP STATUS CODES

Use appropriate status codes.

Examples:

```text
200 OK
201 Created
204 No Content
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Validation Error
500 Internal Server Error
```

---

# 61. TESTING

Backend:

```text
pytest
```

Test:

```text
Registration
Login
JWT
Current user
Lost item creation
Found item creation
Authorization
Ownership
Search
Claims
Notifications
Reports
Admin
```

Frontend:

Use an appropriate React testing framework if needed.

---

# 62. SECURITY TESTS

Test:

```text
Unauthenticated API access
Invalid JWT
Expired JWT
Accessing another user's item
Editing another user's item
Deleting another user's item
Fake user_id
Duplicate email
Invalid file upload
Oversized upload
Admin endpoint access
```

---

# 63. DATABASE TESTS

Verify:

```text
Foreign keys
Unique email
Cascade behavior
Null constraints
Indexes
Relationships
```

---

# 64. PERFORMANCE

Avoid:

```text
N+1 queries
Unnecessary database calls
Loading all records without pagination
Huge image responses
Repeated embedding generation
```

Use:

```text
Pagination
Indexes
Caching where useful
Background tasks
Batch embedding generation
```

---

# 65. PAGINATION

Listing APIs should support:

```text
page
limit
```

Example:

```text
/lost-items?page=1&limit=20
```

Default:

```text
20 items
```

Maximum:

```text
100 items
```

---

# 66. AI PROCESSING

AI processing can become expensive.

Do not regenerate embeddings every time an item is viewed.

Generate when:

```text
Item created
Item meaningfully updated
```

Store or cache the embedding.

---

# 67. BACKGROUND TASKS

AI matching and notification processing may eventually run asynchronously.

Potential architecture:

```text
API
 ↓
Database
 ↓
Background Worker
 ↓
Embedding
 ↓
Matching
 ↓
Notification
```

For the first version, FastAPI background tasks are acceptable.

Later consider:

```text
Celery
Redis
RQ
```

Only introduce them when necessary.

---

# 68. AI FAILURE HANDLING

The application must continue working if AI services fail.

Example:

```text
User reports lost item
       ↓
Database save succeeds
       ↓
AI service unavailable
       ↓
Listing remains available
       ↓
AI matching retries later
```

Never make the entire application dependent on AI availability.

---

# 69. IMAGE PROCESSING FAILURE

If image processing fails:

```text
Do not lose the listing.
```

Show:

```text
Image processing is temporarily unavailable.
Your listing was saved successfully.
```

---

# 70. PRIVACY

Public users should not see:

```text
Private email
Phone number
Password
Exact home address
Private verification answers
JWT
Internal database IDs where unnecessary
```

The system should use approximate locations where appropriate.

---

# 71. FRAUD PREVENTION

Potential safeguards:

```text
Rate limiting
Email verification
Report system
Claim verification
Suspicious activity detection
Duplicate listing detection
Admin moderation
```

Do not automatically ban users based solely on AI.

---

# 72. DUPLICATE DETECTION

Detect duplicate listings using:

```text
Text similarity
Image similarity
Location
User
Time
```

Flag potential duplicates.

Do not automatically delete them without review.

---

# 73. SEARCH ARCHITECTURE

Start with:

```text
MySQL keyword search
```

Then add:

```text
Semantic search
```

Eventually:

```text
Keyword search
+
Semantic search
+
Location
+
Category
```

---

# 74. AI SEARCH

Example:

User searches:

```text
black leather wallet near metro
```

System should understand:

```text
Color: black
Type: wallet
Material: leather
Location: metro
```

Then retrieve relevant items.

---

# 75. FUTURE AI ASSISTANT

Optional future feature:

```text
FindBack AI Assistant
```

Example:

User:

```text
I lost my black wallet yesterday near JNTU.
```

Assistant can guide:

```text
Would you like to report it?

Suggested information:
Category: Wallet
Color: Black
Location: JNTU
Time: Yesterday
```

The AI must ask for confirmation before submitting a report.

---

# 76. ADMIN ANALYTICS

Admin dashboard:

```text
Total users
Active users
Lost reports
Found reports
Donations
Successful returns
Potential matches
Successful matches
Open reports
```

Charts may use Recharts.

---

# 77. SUCCESS METRICS

Track:

```text
Lost items reported
Found items reported
Potential matches
Verified matches
Returned items
Donation claims
Successful donations
Reports
```

Do not expose sensitive analytics publicly.

---

# 78. LOGGING

Backend should use structured logging.

Log:

```text
Request
Response status
Errors
AI failures
Authentication failures
Important system events
```

Never log:

```text
Passwords
JWT tokens
API keys
Private verification answers
```

---

# 79. CONFIGURATION

Centralize configuration.

Example:

```text
app/config.py
```

Use environment variables.

Do not scatter configuration values throughout the project.

---

# 80. CODE QUALITY

Follow:

```text
PEP 8
Type hints
Meaningful names
Small functions
Separation of concerns
DRY principle
```

Frontend:

```text
Reusable components
TypeScript types
Hooks
Service layer
```

---

# 81. API ARCHITECTURE

Use routers.

Example:

```text
/auth
/users
/lost-items
/found-items
/donations
/matches
/claims
/notifications
/reports
/admin
```

Do not keep the entire production application inside `main.py`.

However, refactor the existing code gradually.

---

# 82. FRONTEND COMPONENTS

Reusable components should include:

```text
Navbar
Footer
Button
Input
Modal
Card
ItemCard
SearchBar
FilterPanel
Pagination
LoadingSpinner
EmptyState
ErrorMessage
NotificationBell
ProtectedRoute
```

---

# 83. DESIGN SYSTEM

Use a consistent design.

Primary visual identity:

```text
FindBack
```

Suggested style:

```text
Modern
Minimal
Trustworthy
Friendly
Technology-oriented
Community-focused
```

Do not overuse gradients or animations.

---

# 84. MOBILE EXPERIENCE

Mobile users should be able to:

```text
Register
Login
Report lost item
Report found item
Upload image
Search
View matches
Claim item
Receive notifications
```

without needing desktop.

---

# 85. DEPLOYMENT

Eventually support:

```text
Frontend:
Vercel / Netlify / equivalent

Backend:
Render / Railway / AWS / equivalent

Database:
Managed MySQL
```

AI services should use environment variables.

Do not hardcode production credentials.

---

# 86. DOCKER

Dockerization can be added later.

Potential:

```text
frontend container
backend container
database container
```

Do not introduce Docker until the local application works.

---

# 87. CI/CD

Eventually configure:

```text
GitHub
GitHub Actions
Automated tests
Build
Deployment
```

Pipeline:

```text
Push
 ↓
Lint
 ↓
Test
 ↓
Build
 ↓
Deploy
```

---

# 88. DEVELOPMENT PHASES

Implement in this exact broad order.

## PHASE 1 — FOUNDATION

Complete:

```text
FastAPI
MySQL
SQLAlchemy
Environment configuration
Project structure
```

Status:

```text
PARTIALLY COMPLETE
```

---

## PHASE 2 — AUTHENTICATION

Implement:

```text
Register
Login
JWT
Password hashing
Current user
Logout/token removal
JWT expiration
```

Status:

```text
PARTIALLY COMPLETE
```

---

## PHASE 3 — LOST ITEMS

Implement:

```text
Create
Read
Update
Delete
My listings
Images
Categories
Status
Pagination
Search
Filters
```

---

## PHASE 4 — FOUND ITEMS

Implement:

```text
Create
Read
Update
Delete
My listings
Images
Categories
Status
Pagination
Search
Filters
```

---

## PHASE 5 — FRONTEND FOUNDATION

Implement:

```text
React
Routing
Tailwind
Navbar
Footer
Auth context
Axios
Protected routes
```

---

## PHASE 6 — CORE UI

Implement:

```text
Home
Login
Register
Dashboard
Lost Items
Found Items
Report Lost
Report Found
My Listings
Item Details
```

---

## PHASE 7 — SEARCH AND LOCATION

Implement:

```text
Search
Filters
Location
Nearby items
Pagination
```

---

## PHASE 8 — DONATIONS

Implement:

```text
Donation model
Donation API
Donation UI
Claim flow
```

---

## PHASE 9 — CLAIMS

Implement:

```text
Claims
Verification
Approval
Rejection
Status
```

---

## PHASE 10 — AI TEXT MATCHING

Implement:

```text
Sentence Transformers
Embeddings
FAISS
Similarity
Match model
Match API
```

---

## PHASE 11 — AI IMAGE MATCHING

Implement:

```text
Image upload
Image embeddings
CLIP
Image similarity
Combined matching
```

---

## PHASE 12 — NOTIFICATIONS

Implement:

```text
Notification model
Notification API
Frontend notification UI
Unread count
Potential match notifications
Claim notifications
```

---

## PHASE 13 — REPORTING

Implement:

```text
Report model
Report API
Report UI
Admin review
```

---

## PHASE 14 — ADMIN

Implement:

```text
Admin authentication
Dashboard
Users
Listings
Reports
Claims
Statistics
Moderation
```

---

## PHASE 15 — SECURITY HARDENING

Implement:

```text
JWT expiration
Rate limiting
Input validation
Upload validation
CORS
Secure headers
Error handling
Authorization
```

---

## PHASE 16 — TESTING

Implement:

```text
Unit tests
API tests
Authentication tests
Authorization tests
AI matching tests
Frontend tests
```

---

## PHASE 17 — PERFORMANCE

Implement:

```text
Indexes
Pagination
Caching
Background tasks
Embedding optimization
Database optimization
```

---

## PHASE 18 — DEPLOYMENT

Implement:

```text
Production environment
Environment variables
Frontend deployment
Backend deployment
Database deployment
HTTPS
Monitoring
```

---

# 89. IMPLEMENTATION RULE

Do NOT attempt all phases in a single uncontrolled operation.

For each phase:

```text
Inspect
 ↓
Plan
 ↓
Implement
 ↓
Run
 ↓
Test
 ↓
Fix
 ↓
Document
 ↓
Continue
```

---

# 90. WHEN AN ERROR OCCURS

Do not hide errors.

Investigate:

```text
Traceback
API response
Database error
Browser console
Network request
```

Fix the root cause.

Do not randomly change multiple unrelated files.

---

# 91. DATABASE SAFETY

Never execute destructive commands such as:

```text
DROP DATABASE
DROP TABLE
TRUNCATE
```

unless explicitly required and confirmed.

Never delete existing user data simply to make a feature work.

Use migrations.

---

# 92. EXISTING DATA

The existing development database may contain test users and listings.

Preserve them.

Do not assume IDs.

Never hardcode:

```text
user_id = 1
```

for new application logic.

Always use authenticated user.

---

# 93. LEGACY DATA

If old development records contain insecure test data, create a migration or cleanup procedure.

Do not silently break existing records.

---

# 94. API BACKWARD COMPATIBILITY

When modifying an existing endpoint:

1. Inspect existing frontend usage.
2. Inspect existing Swagger behavior.
3. Preserve response fields where possible.
4. Update frontend together with backend if breaking changes are necessary.
5. Document breaking changes.

---

# 95. GIT COMMITS

Use meaningful commits.

Examples:

```text
feat: add found item CRUD APIs
feat: add donation workflow
feat: add AI text matching
feat: add notification system
fix: validate item ownership
refactor: move item routes into routers
test: add authentication tests
```

---

# 96. README PROGRESS TRACKING

Maintain:

```text
PROJECT PROGRESS
```

Example:

```text
[✓] FastAPI setup
[✓] MySQL setup
[✓] User authentication
[✓] Lost item creation
[✓] Found item creation
[ ] Found item CRUD
[ ] React frontend
[ ] Donations
[ ] AI matching
[ ] Image matching
[ ] Notifications
[ ] Claims
[ ] Admin
[ ] Deployment
```

Update this section whenever a major feature is completed.

---

# 97. DEFINITION OF COMPLETE APPLICATION

FindBack is considered feature-complete when:

```text
Users can register
        ↓
Users can login
        ↓
Users can report lost items
        ↓
Users can report found items
        ↓
Users can donate items
        ↓
Users can search
        ↓
Users can filter
        ↓
Users can find nearby items
        ↓
AI identifies potential matches
        ↓
Users receive notifications
        ↓
Users submit claims
        ↓
Ownership is verified
        ↓
Items can be returned
        ↓
Donations can be claimed
        ↓
Users can report suspicious content
        ↓
Admins can moderate
```

---

# 98. MOST IMPORTANT PRODUCT PRINCIPLE

FindBack is not simply a CRUD application.

The important value comes from:

```text
Community
+
Search
+
Location
+
AI
+
Verification
+
Trust
```

Every implementation decision should support these principles.

---

# 99. TRUST PRINCIPLE

Never allow AI to make irreversible decisions.

AI can:

```text
Suggest
Rank
Classify
Explain
Detect
```

AI should not independently:

```text
Confirm ownership
Ban users
Delete listings
Approve claims
```

Human/user/admin confirmation should be used for important actions.

---

# 100. FINAL OPENCODE INSTRUCTION

After reading this document:

1. Inspect the entire existing repository.
2. Identify what has already been implemented.
3. Identify incomplete functionality.
4. Do not overwrite or delete working code.
5. Create a development plan based on the phases above.
6. Start from the earliest incomplete phase.
7. Implement that phase completely.
8. Run the backend/frontend.
9. Test the implemented functionality.
10. Fix errors.
11. Update documentation.
12. Update the progress checklist.
13. Only then continue to the next phase.

Do not stop after creating a plan.

The objective is to actually build the complete FindBack application.

When a feature is completed, provide a concise summary containing:

```text
What was implemented
Files changed
Database changes
API changes
Frontend changes
Tests performed
Remaining work
```

Always preserve existing functionality.

Always prioritize security, maintainability, correctness, and a good user experience.

---

# PROJECT PROGRESS

Maintained during development. Last updated: 2026-10-02

Legend: `[✓]` complete · `[~]` partially complete · `[ ]` not started

## Backend

```text
[✓] FastAPI setup (modular routers, CORS, structured logging, Swagger /docs)
[✓] MySQL setup (existing `findback` database and data preserved)
[✓] SQLAlchemy models (users, lost_items, found_items, donations, claims, matches, notifications, reports)
[✓] Environment configuration (.env + .env.example, no secrets in code, config.py single source)
[✓] Non-destructive schema migration (create_tables.py only ADDS missing columns/indexes)
[✓] User registration (POST /users legacy + POST /auth/register)
[✓] Password hashing (bcrypt)
[✓] JWT login + JWT expiration (POST /login form + POST /auth/login JSON)
[✓] Current user (GET /me) + suspended-account guard
[✓] Lost item CRUD (POST/GET/PUT/DELETE /lost-items, GET /lost-items/{id})
[✓] Lost item pagination, keyword search, category/location/status/date filters, distance filter
[✓] My lost items (GET /my-lost-items)
[✓] Found item CRUD (POST/GET/PUT/DELETE /found-items, GET /found-items/{id})
[✓] Found item pagination, search, filters
[✓] My found items (GET /my-found-items)
[✓] Ownership enforcement: user_id always from JWT, 403 for non-owners, admin override
[✓] Unified search (GET /search across LOST/FOUND/DONATION) + GET /nearby + GET /stats
[✓] Donations API (CRUD, filters, my-donations, claim endpoint)
[✓] Claims API (create/approve/reject/cancel, received, privacy, verification answers)
[✓] AI text matching (embeddings with fallback backend, vector index abstraction, match explanations)
[✓] Background matching on create/update + manual rebuild endpoints
[✓] Image matching (magic-byte validated uploads, /media static, identical-image score, optional CLIP)
[✓] Notifications API (list, unread-count, read, read-all) + creation on matches/claims/reports
[✓] Reporting API (user-facing create/mine + admin queue/review)
[✓] Admin API (stats, users suspend/activate/role, listings moderation, claims, reports, global rebuild)
[✓] Rate limiting / security hardening (sliding window, auth bucket, security headers, JSON 500)
[✓] Backend test suite (42 pytest tests against findback_test database)
[✓] Health endpoint (GET /health)
```

## Frontend

```text
[✓] React + TypeScript + Vite scaffold (npm run build passes: tsc -b + vite)
[✓] Tailwind CSS (v4 via @tailwindcss/vite, shared .btn/.input/.card utilities)
[✓] Routing + Navbar/Footer (19 pages, protected/admin routes, unread badge)
[✓] Auth context + Axios client + protected routes (JWT localStorage, 401 auto-logout)
[✓] Home / Login / Register pages (live stats, register+auto-login verified in browser)
[✓] Dashboard (tabs: my lost / found / donations / claims with counts)
[✓] Lost / Found listings + details + report forms (create verified: /lost/13, /found/8)
[✓] My Listings / Profile (profile info, re-run AI matching, logout verified)
[✓] Search & filters UI (unified search across lost/found/donation)
[✓] Donations UI (list, filters, claim, create form)
[✓] Matches UI (score breakdown, explanation + disclaimer, status updates)
[✓] Notifications UI (unread badge, mark read / mark all read)
[✓] Admin UI (stats, users moderation, listings, reports, claims; non-admin redirected)
```

Browser-verified end-to-end on 2026-10-02 (Vite dev server + live backend): register →
auto-login, protected routes, lost/found create (items /lost/13, /found/8), background AI
match (91% score with explanation), notifications + unread badge, unified search,
donations list, dashboard tabs, profile/logout, admin stats + suspend/activate roundtrip,
non-admin → / redirect. Fixes found during UI testing: CORS now wraps the rate-limit
middleware so 429 responses carry `Access-Control-Allow-Origin`; `X-RateLimit-Limit` added
to 429s and both headers exposed to browser JS; match-notification wording fix
("your lost/found item report"). `npm run build` green; pytest still 42/42.

## Database (live `findback` schema)

```text
[✓] users (existing data preserved; added role, is_active, created_at, updated_at)
[✓] lost_items (existing data preserved; added category, status, lat/lon, images, timestamps)
[✓] found_items (added category, status, lat/lon, images, timestamps)
[✓] donations (new)
[✓] claims (new)
[✓] matches (new)
[✓] notifications (new)
[✓] reports (new)
```

## Decisions log

- **2026-10-02 — Project location:** existing backend from `Desktop\findback` was copied into
  `opencodepj/backend` (original left untouched) so the repo root matches the structure in §7;
  the existing venv is reused for running the app.
- **2026-10-02 — Phase order:** all backend phases (1–4, 7–14, 15–16) are implemented before the
  frontend phases (5–6) so the UI is built once against a stable, complete API.
- **2026-10-02 — Migrations:** `create_tables.py` + `app/migrations.py` perform additive-only
  schema changes (ALTER TABLE ADD COLUMN / CREATE INDEX) because Alembic is not yet adopted;
  nothing is ever dropped or truncated (§57, §91).
- **2026-10-02 — Response format:** list endpoints return `{items, total, page, limit, pages}`;
  mutations return `{message, ...}`; single-resource GET returns the resource object directly.
  Legacy response keys from the original implementation are preserved.

---

# END OF MASTER README
