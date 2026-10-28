# Campus Structural Health Survey and Maintenance Planning App

A Python-based, interactive web application developed using Streamlit to document the structural condition of institutional campus buildings, record defects, plan investigations, estimate repair costs, and generate inspection reports.

## Project Overview

The Campus Structural Health Survey App supports preliminary condition surveys of institutional buildings, particularly reinforced cement concrete (RCC) framed buildings. It provides a structured platform for recording visible defects, maintaining investigation records, preparing preliminary repair estimates, and generating reports.

The application is intended for use by civil engineers, building maintenance teams, facility managers, and institutional administrators.

## Features

- **Building Register:** Record building names, construction years, number of storeys, structural systems, and inspection details.
- **Defect Survey:** Document cracks, concrete spalling, exposed reinforcement, corrosion, dampness, water leakage, plaster deterioration, and other visible defects.
- **Photo Documentation:** Upload and associate photographs with individual defect records.
- **Investigation Register:** Record proposed and completed investigations, including rebound hammer testing, ultrasonic pulse velocity (UPV), reinforcement cover surveys, carbonation testing, and other specialist investigations.
- **Repair BOQ:** Enter measured quantities, units, unit rates, repair priorities, and calculate preliminary repair costs.
- **Dashboard:** View building records, defect summaries, investigation records, and estimated repair costs.
- **PDF Reports:** Generate campus or building-level condition survey reports.
- **Data Export:** Export building, defect, testing, and BOQ records to CSV files.
- **Local Database:** Store survey records using SQLite.

## Technology Stack

- Python
- Streamlit
- Pandas
- SQLite
- ReportLab

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
```

Replace `YOUR-USERNAME` and `YOUR-REPOSITORY` with your actual GitHub username and repository name.

### 2. Install dependencies

Ensure Python is installed, then run:

```bash
pip install -r requirements.txt
```

### 3. Run the application

Execute the following command:

```bash
streamlit run app.py
```

The application will open in your browser, usually at:

```text
http://localhost:8501
```

## Deployment

The application can be deployed using Streamlit Community Cloud.

1. Push `app.py`, `requirements.txt`, and `README.md` to a GitHub repository.
2. Visit https://share.streamlit.io/
3. Connect your GitHub account.
4. Select the repository and choose `app.py` as the application entry point.
5. Deploy the application.

For reliable multi-user operation, the application should be upgraded to use a managed database, persistent photo storage, authentication, and appropriate access controls.

## Application Workflow

1. Register campus buildings.
2. Select a building and record observed defects.
3. Upload defect photographs and document measurements.
4. Record proposed investigations and test results.
5. Enter repair items, measured quantities, and verified rates.
6. Review the dashboard and preliminary repair estimate.
7. Generate a PDF report and export survey data.

## Data Storage

The current version uses a local SQLite database named `campus_survey.db` and stores uploaded photographs in the `survey_photos/` directory.

**Important:** Local files on a hosted platform may not provide durable storage. Back up the database and photographs regularly. For official campus records and multiple surveyors working simultaneously, use persistent cloud storage and a shared database.

## Engineering Disclaimer

This application is a documentation and maintenance-planning tool. It does not independently determine structural capacity, certify building safety, or replace a detailed structural assessment.

Defect classifications, investigation requirements, repair methods, and final repair quantities must be reviewed by qualified professionals. Where critical structural distress or a potential immediate hazard is observed, restrict access as appropriate and obtain an urgent assessment from a qualified structural engineer.

Repair estimates are preliminary and depend on the quantities and rates entered by the user. They should be verified against applicable specifications, local schedules of rates, site conditions, and approved repair methods.

## Future Enhancements

- Multi-user authentication and role-based access.
- Cloud database and persistent image storage.
- Building and floor plan mapping.
- Editable defect records and inspection history.
- Automated repair priority matrix.
- Excel and detailed BOQ report generation.
- Integration with sensor-based structural health monitoring systems.
- AI-assisted image classification, subject to validation by qualified professionals.

## License

Choose an appropriate open-source license before distributing or reusing this project. For example, the MIT License permits reuse subject to its terms.

## Author

Developed as a digital tool for campus building condition surveys, structural maintenance planning, and preliminary repair cost estimation.
