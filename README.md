# **WIMS – Multi-Tenant Workflow System**

## 1. Introduction

WIMS (Workflow & Information Management System) is a complete multi-tenant ERP + CRM platform designed for educational institutions, coaching centers, and enterprise training providers. It automates all workflows from enquiries to admissions, course delivery, staff management, fees, e-learning, and reporting.

This documentation provides a complete technical + business overview of the entire system.

---

## 2. System Overview

WIMS is engineered using Django, Django REST Framework, and a multi-database design.

### **Key Capabilities**

* Student lifecycle automation
* Course & batch management
* E-learning modules (folders, quizzes, assignments)
* Fee management, invoices, transactions
* Staff roles & permissions
* Multi-database tenant isolation
* JWT + Session hybrid authentication
* Activity logs, audit logs, notifications
* Large-scale import/export via Excel & CSV

---

## 3. Multi-Tenant Architecture

WIMS uses a **Shared-Main DB + Isolated-Client DB** structure.

### **3.1 Shared Main Database**

Holds:

* User accounts (Admin, Sub-Admin, Staff)
* Client master details
* Global master tables
* Permissions & roles

### **3.2 Client-Specific Database**

Each client has its own database storing:

* Enquiries
* Registrations
* Admissions
* Course content
* Staff details (optional)
* Fees, payments, invoices
* Quiz data, attempts

### **3.3 Why This Architecture**

* High security (client data isolation)
* Easy horizontal scaling
* Independent backup/restore per client
* Zero performance leakage between tenants

---

## 4. Application Modules Overview

### **4.1 Users App**

Manages:

* Authentication (JWT + Session)
* Role-based access
* Dynamic custom roles
* User permissions

### **4.2 Master App**

Stores global data:

* Nationality
* Course categories
* Countries, states, cities
* Admission sources
* Status tables

### **4.3 Staff App**

Handles:

* Staff registration
* Staff permissions
* Staff role mapping

### **4.4 Course & Batch App**

Responsible for:

* Course creation
* Module & topic hierarchy
* Batch creation
* Assignments & materials

### **4.5 student_details App**

Manages early student workflows:

* Enquiry
* Follow-up
* Registration

### **4.6 Admission App**

Handles:

* Admission forms
* Document uploads
* Batch assignment

### **4.7 Fee_Details App**

Contains:

* Fee structure
* Fee payments
* Receipts & invoices

### **4.8 E-Learning App**

Includes:

* Folder management
* Quiz creation
* MCQ questions
* Attempts & scoring

---

## 5. Models Summary

### **5.1 User Model**

* id
* email
* name
* role (admin, sub-admin, staff, student)
* client_code
* dynamic_permissions

### **5.2 Course Models**

* Course
* Batch
* Module
* Topic

### **5.3 Student Models**

* Enquiry
* FollowUp
* Registration
* StudentProfile

### **5.4 Admission Models**

* AdmissionRecord
* AdmissionDocuments

### **5.5 Fees Models**

* FeeStructure
* FeePayment
* Invoice

### **5.6 E-Learning Models**

* Folder
* Quiz
* MCQQuestion
* MCQAnswer
* StudentAttempt

---

## 6. Workflow Diagrams

### **6.1 Student Lifecycle**

```
Enquiry → Follow-Up → Registration → Admission → Fees → Course → Certification
```

### **6.2 Course Lifecycle**

```
Course → Modules → Topics → Assignments → Quiz → Evaluation
```

### **6.3 Permission Flow**

```
Role → Permissions → Assign to User → User Access Granted
```

---

## 7. Authentication Architecture (JWT + Session)

### **7.1 JWT Authentication**

Used for:

* Students
* Staff
* Sub-admins

### **7.2 Session Authentication**

Used for:

* Admin portal
* Secure backend access

### **7.3 Token Strategy**

* Access token: Short-lived
* Refresh token: Long-lived
* Safe rotation

---

## 8. Database Router & Tenant DB Management

### **8.1 Routing Logic**

* Users → Main DB
* Staff → Main DB
* Student data → Client DB
* Course data → Client DB

### **8.2 Dynamic Client Database Creation**

Steps:

1. Admin creates a client
2. System generates a new PostgreSQL DB
3. Applies migrations automatically
4. Registers DB into settings

### **8.3 Query Flow**

```
Request → Middleware → Client Code Detection → DB Router → Target Database
```

---

## 9. API Endpoints Overview

### **9.1 User APIs**

* /login
* /refresh
* /register-staff
* /assign-permissions

### **9.2 Course APIs**

* /courses/create
* /courses/modules
* /courses/topics

### **9.3 Student APIs**

* /enquiry/create
* /registration
* /admission
* /fee/pay

### **9.4 E-Learning APIs**

* /folder/create
* /quiz/create
* /quiz/questions
* /quiz/attempt

---

## 10. Deployment & Configuration

### **10.1 Environment Requirements**

* Python 3.12+
* PostgreSQL
* Gunicorn
* NGINX

### **10.2 Environment Variables**

* DATABASE_URL
* JWT_SECRET_KEY
* EMAIL_HOST configurations

---

## 11. Future Enhancements

* Real-time dashboards
* Student mobile app
* AI-powered recommendations
* Advanced LMS integration
* WebRTC-based live classes


## 12. WorkFLow

* Creates a SuperAdmin
* Login super_admin
* Create Clients
* Migrate apps for a specific tenant
* Select Client
* ClientAdmin can Login to their DB

