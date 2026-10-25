# DermAI Project Documentation

## 1. Project title

**DermAI — Skin Image Analysis and Case Workspace**

## 2. Project overview

DermAI is an educational prototype for collecting, validating, organizing, and preparing skin images for a future skin-condition classification system. The current application provides a React/Vite/TypeScript browser interface, a FastAPI backend, PostgreSQL persistence, authenticated case management, image-upload validation, and an image-preprocessing function.

The current application does **not** diagnose skin disease and does not run model inference. Classification is a planned extension.

## 3. Problem statement

Skin-image projects need a consistent workflow for identifying a case, associating images with that case, validating image inputs, and preparing data before a model can be evaluated. Without that workflow, images, annotations, and future results can become difficult to trace or compare.

## 4. Motivation and intended users

The intended users are students, project demonstrators, and developers working with de-identified educational skin-image datasets. The application is designed to demonstrate responsible data handling and a clear separation between image preparation and future model inference.

## 5. Primary objective

Build a reproducible educational foundation that can receive and organize skin images, validate them, prepare them for later experimentation, and preserve user/case ownership boundaries.

## 6. Specific objectives

- Use the DermaCon-IN metadata and locally extracted image artifacts for reproducible analysis.
- Understand the metadata annotations and their class imbalance.
- Provide registration and login through the existing FastAPI backend.
- Allow authenticated users to create, list, edit, close, and delete their own cases.
- Validate JPG, JPEG, and PNG uploads with a 10 MB limit.
- Associate validated upload metadata with an owned case when requested.
- Resize readable images to 224 × 224 RGB arrays and normalize them to `[0, 1]` when the preprocessing function is explicitly invoked.
- Document the architecture and dataset evidence without overstating current AI capabilities.

## 7. Project scope

### In scope

- Dataset metadata inspection and reproducible EDA.
- Browser-based authentication, dashboard, case management, and image-upload screens.
- FastAPI endpoints for authentication, cases, uploads, health, and existing prediction-history reads.
- PostgreSQL users, cases, case-image metadata, and prediction-history tables.
- Pillow/NumPy preprocessing.

### Out of scope for the current milestone

- Training a deep-learning model.
- Disease prediction or inference.
- Clinical decision support or diagnosis.
- Clinical validation, treatment advice, or medical certification.
- Cloud deployment and production operations.

## 8. Functional requirements

| Requirement | Status | Evidence |
|---|---|---|
| User registration and login | IMPLEMENTED | `backend/app/auth.py`, `/auth/register`, `/auth/login` |
| Verified authorization for protected operations | IMPLEMENTED | HMAC bearer-token verification in `backend/app/auth.py` |
| Case creation and listing | IMPLEMENTED | `backend/app/cases.py`, `/cases` |
| Case update and deletion | IMPLEMENTED | `backend/app/cases.py`, `PATCH` and `DELETE /cases/{case_id}` |
| Case-image association | IMPLEMENTED | `case_images` table and `POST /images/upload?case_id=...` |
| Upload validation | IMPLEMENTED | `backend/app/uploads.py`, `POST /images/upload` |
| Image preprocessing | IMPLEMENTED | `ai/image_preprocessing.py` |
| Browser frontend | IMPLEMENTED | `frontend/src/` |
| Disease inference | PLANNED | No model or inference endpoint exists |

## 9. Non-functional requirements

- **Reproducibility:** EDA uses repository-relative paths and deterministic calculations.
- **Data isolation:** Case queries filter by the authenticated user ID.
- **Credential safety:** Passwords are stored as scrypt hashes; database credentials and secrets are not in frontend source.
- **Input validation:** Pydantic validates case/auth inputs; Pillow validates image readability.
- **Maintainability:** Backend responsibilities are separated into authentication, database, uploads, and cases modules.
- **Transparency:** Reports distinguish implemented behavior from planned inference.

## 10. Existing features

The application currently supports:

1. React/Vite/TypeScript browser pages for login, registration, dashboard, cases, case editing, and image upload.
2. FastAPI health endpoints and PostgreSQL connectivity checks.
3. Registration with password hashing and login with a signed access token.
4. Authenticated case CRUD with user ownership checks.
5. Optional association of validated upload metadata with a case.
6. Existing `prediction_history` reads, kept separate from case management.
7. Dataset preparation and subject-grouped train/validation/test split artifacts.
8. Preprocessing to RGB, 224 × 224, `float32`, and `[0, 1]`.

## 11. Planned future features

- Select and approve a final target-class scope based on the EDA report.
- Train and evaluate a classifier using a documented split and evaluation protocol.
- Add a model-inference service or endpoint only after model validation.
- Associate verified model outputs with cases without replacing raw case or upload metadata.
- Add model performance reporting and appropriate uncertainty communication.

## 12. Assumptions and limitations

- The repository identifies the working dataset as DermaCon-IN, but no authoritative citation, license, or source URL was found in the repository. Those details require confirmation before external redistribution.
- The local extracted image directory contains only the locally available subset; unmatched metadata records may reflect extraction state.
- The application is an educational prototype and is not a diagnostic medical device.
- The current token format has no expiration claim.
- Upload validation stores case-image metadata, not the image binary itself.
- Target classes have not been finalized by project-owner approval.

## 13. Expected outcome

At the end of this milestone, DermAI provides a traceable, testable foundation for future research: users can create cases, validate and associate images, inspect dataset evidence, and invoke preprocessing explicitly. Future classification work can be added without confusing case records with prediction history or presenting unvalidated predictions as diagnoses.

## 14. Intended workflow

1. User opens DermAI.
2. User registers or logs in.
3. User accesses the dashboard.
4. User creates or selects a case.
5. User uploads a JPG, JPEG, or PNG image.
6. FastAPI validates the file type, size, and readability.
7. If a case is selected, validated image metadata is associated with an owned case.
8. The existing preprocessing function can be invoked explicitly by a future workflow; upload does not automatically call it.
9. A future trained model may analyze a prepared image.
10. Future results may be associated with the case and displayed with appropriate limitations.
11. The user can continue managing cases and relevant records.
