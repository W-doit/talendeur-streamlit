# 🚀 CV Parser Microservice

A tool designed to extract and structure information from LinkedIn PDF resumes into standardized JSON professional profiles.

## 🏗️ Technical Architecture
The system is built as a **Serverless Microservice** optimized for deployment on **Netlify**.

* **Core Framework:** FastAPI (Python 3.13+)
* **NLP Engine:** SpaCy (`en_core_web_sm`)
* **PDF Extraction:** `pdfplumber` for coordinate-based text reading.
* **Serverless Adapter:** Mangum (for Netlify/AWS Lambda compatibility).

## 📂 Project Structure
```text
talendeur-streamlit/
├── api/
│   ├── main_talendeur.py                              # API Endpoints & Mangum Handler
│   └── LinkedIn_PDF_Reader_Talendeur_for_microservices.py # Core NLP Engine
├── netlify.toml                                       # Deployment configuration
├── requirements.txt                                   # Project dependencies
└── README.md                                           # Documentation


## 🧠 Core Logic & Extraction Heuristics

The engine goes beyond simple anchor detection, utilizing a hybrid approach that combines spatial coordinates with text-pattern analysis to classify data types.

### 1. Spatial Segmentation (Anchors)
The engine identifies primary headers (e.g., *Experience*) by scanning the vertical ($y$-axis) position. This creates "Contextual Buckets" where the data is contained.

### 2. Format-Based Classification (Heuristics)
Inside each segment, the parser uses a mix of specialized accessory functions to determine the nature of each text line:
* **Entity Validation**: Functions like `is_company()` or `is_location()` analyze font styles and known patterns to distinguish a Company Name from a Job Role.

* **Country & Location Mapping**: Integrates `pycountry` and custom dictionaries to normalize geographical data, even when formatted inconsistently in the PDF.

* **Type Identification**: Distinguishes between "Body Text" (descriptions) and "Metadata" (dates, locations, or titles) based on their horizontal indentation and proximity to other elements.

### 3. Multi-Dimensional Skill Mapping
Extracted tokens are cross-referenced against a thematic taxonomy to group professional capabilities into strategic dimensions (Leadership, Strategic Thinking, etc.), providing a more holistic view of the candidate than a flat list of keywords.

## 🛠️ Main Functions

### `CVParser.extract_text_with_coordinates()`
The primary data extractor. It captures text strings along with their precise $(x, y)$ coordinates to preserve the document's original structure.

### `CVParser.parse_experience()`
A state-aware function that iterates through the Experience block. It uses the accessory functions to decide if a line represents a new company entry or a continuation of a previous role.

### `accessory_functions` (Validation Logic)
A suite of helper functions (including Regex and dictionary lookups) that act as "validators" to confirm:
* **Dates**: Normalizing varied formats (e.g., "Present", "2023", "Oct-22").
* **Contact Data**: Identifying emails and phone numbers via pattern recognition.
* **Geographical Entities**: Mapping cities and countries to standard ISO codes.

## 🌐 Deployment Logic
This service uses a netlify.toml configuration to:

Automated Build: Install dependencies and download SpaCy models during the build phase.

Serverless Execution: Convert the FastAPI app into a Lambda-compatible function via Mangum.

