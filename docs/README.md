# Smart Inventory Management System (SIMS) - Documentation Index

Welcome to the technical documentation repository for the **Smart Inventory Management System (SIMS)**. This directory contains specifications, architectural diagrams, API contracts, and development team guidelines.

---

## 📁 Documentation Structure

```
docs/
├── README.md                      # Documentation hub (this file)
├── API/                           # REST API specifications and testing collections
│   ├── api_specification.md       # Comprehensive REST API contracts & schemas
│   └── postman_collection.json    # Importable Postman Collection (v2.1.0)
├── SRS/                           # Software Requirements Specifications
│   └── SRS_Document.md            # IEEE 830-aligned requirements document
├── UML/                           # Visual Architecture & System Models
│   └── UML_Diagrams.md            # Mermaid-rendered ERD, Use Case, Sequence & Architecture diagrams
└── project-notes/                 # Collaboration, Onboarding & Roadmaps
    ├── team_responsibilities_matrix.md  # Multi-team domain split & Git workflow
    ├── database_setup_guide.md          # PostgreSQL setup, config, and snapshot restore
    └── sprint_meeting_notes.md          # Sprint milestones, blockers, and next steps
```

---

## 🎯 Quick Navigation

| Document | Purpose | Target Audience |
| :--- | :--- | :--- |
| [API Specification](file:///f:/Smart%20Inventory%20Management%20System/docs/API/api_specification.md) | Exhaustive REST endpoint references, payloads, status codes, and auth rules | Frontend & Backend Developers |
| [Postman Collection](file:///f:/Smart%20Inventory%20Management%20System/docs/API/postman_collection.json) | Ready-to-import API test collection with environments and samples | QA Engineers & Testers |
| [SRS Document](file:///f:/Smart%20Inventory%20Management%20System/docs/SRS/SRS_Document.md) | Formal functional/non-functional requirements & user personas | Evaluators, Leads & Stakeholders |
| [UML & ERD Diagrams](file:///f:/Smart%20Inventory%20Management%20System/docs/UML/UML_Diagrams.md) | Interactive Mermaid diagrams of database tables, actors, and sequence flows | Architects & System Designers |
| [Team Responsibilities](file:///f:/Smart%20Inventory%20Management%20System/docs/project-notes/team_responsibilities_matrix.md) | Domain ownership across Team 1, Team 2, and Team 3 | Collaborative Development Teams |
| [Database Setup Guide](file:///f:/Smart%20Inventory%20Management%20System/docs/project-notes/database_setup_guide.md) | PostgreSQL configuration, schema migrations, and backup restoration | DevOps & New Contributors |
| [Sprint Meeting Notes](file:///f:/Smart%20Inventory%20Management%20System/docs/project-notes/sprint_meeting_notes.md) | Development history, integration checkpoints, and roadmaps | Project Managers & Team Members |

---

## 🏗️ System Overview

The system is organized into a 3-tier decoupled architecture:
1. **Frontend**: Static Web client (HTML5, CSS3, Vanilla JS modular scripts per team).
2. **Backend**: Python Flask REST API structured with Application Factory (`create_app`), modular Blueprints, and isolated Service layers.
3. **Database**: PostgreSQL relational database comprising 15 normalized tables with automated point-in-time JSON snapshots.

