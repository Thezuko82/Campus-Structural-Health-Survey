
import os
import io
import sqlite3
import uuid
from datetime import date, datetime
from xml.sax.saxutils import escape

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak
)

# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

APP_TITLE = "Campus Structural Health Survey"
DB_FILE = "campus_survey.db"
PHOTO_DIR = "survey_photos"

os.makedirs(PHOTO_DIR, exist_ok=True)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Campus Structural Health Survey")
st.caption(
    "Building condition assessment, defect documentation, "
    "investigation planning and repair cost estimation"
)

# ============================================================
# DATABASE
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS buildings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            campus TEXT,
            address TEXT,
            year_built INTEGER,
            storeys INTEGER,
            structural_system TEXT,
            inspected_by TEXT,
            inspection_date TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            floor TEXT,
            room TEXT,
            element TEXT,
            defect_type TEXT,
            severity TEXT,
            location_detail TEXT,
            length_m REAL DEFAULT 0,
            width_mm REAL DEFAULT 0,
            area_m2 REAL DEFAULT 0,
            quantity REAL DEFAULT 0,
            observation TEXT,
            recommended_action TEXT,
            urgency TEXT,
            photo_path TEXT,
            status TEXT DEFAULT 'Open',
            inspection_date TEXT,
            FOREIGN KEY(building_id) REFERENCES buildings(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            location TEXT,
            element TEXT,
            test_name TEXT,
            purpose TEXT,
            status TEXT,
            result TEXT,
            recommendation TEXT,
            test_date TEXT,
            cost REAL DEFAULT 0,
            FOREIGN KEY(building_id) REFERENCES buildings(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS boq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            item TEXT,
            description TEXT,
            unit TEXT,
            quantity REAL DEFAULT 0,
            rate REAL DEFAULT 0,
            priority TEXT,
            notes TEXT,
            FOREIGN KEY(building_id) REFERENCES buildings(id)
                ON DELETE CASCADE
        );
        """)


init_database()


def read_table(table, building_id=None):
    allowed = {"buildings", "defects", "tests", "boq"}
    if table not in allowed:
        raise ValueError("Invalid table")

    query = f"SELECT * FROM {table}"
    params = ()

    if building_id is not None and table != "buildings":
        query += " WHERE building_id = ?"
        params = (int(building_id),)

    query += " ORDER BY id DESC"

    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def execute_sql(query, params=()):
    with get_connection() as conn:
        conn.execute(query, params)


def get_buildings():
    return read_table("buildings")


def building_label(row):
    return f"{row['name']} (ID: {row['id']})"


# ============================================================
# BUILDING SELECTION
# ============================================================

buildings = get_buildings()

if not buildings.empty:
    building_options = {
        building_label(row): int(row["id"])
        for _, row in buildings.iterrows()
    }
    selected_label = st.sidebar.selectbox(
        "Select building",
        list(building_options.keys())
    )
    selected_building_id = building_options[selected_label]
else:
    building_options = {}
    selected_building_id = None
    st.sidebar.info("Add a building to start the survey.")

st.sidebar.markdown("---")
st.sidebar.caption("Local database: campus_survey.db")
st.sidebar.caption("Keep backups of the database and photo folder.")

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def money(value):
    return f"₹{float(value or 0):,.2f}"


def save_uploaded_photo(uploaded_file):
    if uploaded_file is None:
        return ""

    extension = os.path.splitext(uploaded_file.name)[1].lower()
    if extension not in [".jpg", ".jpeg", ".png", ".webp"]:
        extension = ".jpg"

    filename = f"{uuid.uuid4().hex}{extension}"
    path = os.path.join(PHOTO_DIR, filename)

    with open(path, "wb") as file:
        file.write(uploaded_file.getbuffer())

    return path


def safe_text(value):
    if pd.isna(value):
        return ""
    return str(value)


# ============================================================
# PDF REPORT GENERATOR
# ============================================================

def generate_pdf(building_id=None):
    building_df = read_table("buildings")
    defects_df = read_table("defects", building_id)
    tests_df = read_table("tests", building_id)
    boq_df = read_table("boq", building_id)

    if building_id is not None:
        building_df = building_df[
            building_df["id"] == int(building_id)
        ]

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=17,
        leading=21
    ))

    story = [
        Paragraph("CAMPUS STRUCTURAL CONDITION SURVEY", styles["ReportTitle"]),
        Spacer(1, 5 * mm),
        Paragraph(
            "Condition documentation and maintenance planning report",
            styles["Normal"]
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            f"Report generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
            styles["Normal"]
        ),
        Spacer(1, 5 * mm)
    ]

    story.append(Paragraph("1. Building Register", styles["Heading2"]))

    building_columns = [
        ("name", "Building"),
        ("campus", "Campus"),
        ("year_built", "Year Built"),
        ("storeys", "Storeys"),
        ("structural_system", "System"),
        ("inspected_by", "Inspector"),
        ("inspection_date", "Inspection Date")
    ]

    rows = [[heading for _, heading in building_columns]]
    for _, row in building_df.iterrows():
        rows.append([
            safe_text(row.get(column, ""))
            for column, _ in building_columns
        ])

    if len(rows) == 1:
        rows.append(["No building records"] + [""] * 6)

    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24476B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F0F4F8")])
    ]))
    story.extend([table, Spacer(1, 5 * mm)])

    # Defect summary
    story.append(Paragraph("2. Defect Summary", styles["Heading2"]))

    if defects_df.empty:
        story.append(Paragraph("No defects recorded.", styles["Normal"]))
    else:
        summary = defects_df.groupby(
            ["severity"], dropna=False
        ).size().reset_index(name="Count")

        summary_rows = [["Severity", "Number of Defects"]]
        for _, row in summary.iterrows():
            summary_rows.append([
                safe_text(row["severity"]), str(row["Count"])
            ])

        table = Table(summary_rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24476B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8)
        ]))
        story.extend([table, Spacer(1, 4 * mm)])

        defect_headers = [
            "ID", "Floor/Room", "Element", "Defect",
            "Severity", "Location", "Observation",
            "Recommended Action", "Status"
        ]
        defect_rows = [defect_headers]

        for _, row in defects_df.iterrows():
            defect_rows.append([
                safe_text(row.get("id")),
                safe_text(row.get("floor")) + "/" +
                safe_text(row.get("room")),
                safe_text(row.get("element")),
                safe_text(row.get("defect_type")),
                safe_text(row.get("severity")),
                safe_text(row.get("location_detail")),
                safe_text(row.get("observation"))[:180],
                safe_text(row.get("recommended_action"))[:180],
                safe_text(row.get("status"))
            ])

        wrapped_rows = []
        for row in defect_rows:
            wrapped_rows.append([
                Paragraph(escape(str(cell)), styles["BodyText"])
                for cell in row
            ])

        table = Table(
            wrapped_rows,
            repeatRows=1,
            colWidths=[
                9*mm, 19*mm, 20*mm, 20*mm, 18*mm,
                25*mm, 37*mm, 48*mm, 16*mm
            ]
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24476B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F0F4F8")])
        ]))
        story.extend([table, Spacer(1, 5 * mm)])

    # Investigation register
    story.append(Paragraph("3. Investigation and Testing Register",
                           styles["Heading2"]))

    if tests_df.empty:
        story.append(Paragraph("No tests recorded.", styles["Normal"]))
    else:
        test_rows = [[
            "Location", "Element", "Test", "Purpose",
            "Status", "Result", "Recommendation", "Cost (INR)"
        ]]

        for _, row in tests_df.iterrows():
            test_rows.append([
                safe_text(row.get("location")),
                safe_text(row.get("element")),
                safe_text(row.get("test_name")),
                safe_text(row.get("purpose"))[:150],
                safe_text(row.get("status")),
                safe_text(row.get("result"))[:150],
                safe_text(row.get("recommendation"))[:150],
                money(row.get("cost", 0))
            ])

        table = Table(test_rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24476B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))
        story.extend([table, Spacer(1, 5 * mm)])

    # BOQ
    story.append(Paragraph("4. Preliminary Repair BOQ", styles["Heading2"]))

    if boq_df.empty:
        story.append(Paragraph("No repair items recorded.", styles["Normal"]))
    else:
        boq_rows = [[
            "Item", "Description", "Unit", "Quantity",
            "Rate (INR)", "Amount (INR)", "Priority"
        ]]

        total = 0.0
        for _, row in boq_df.iterrows():
            amount = float(row["quantity"] or 0) * float(row["rate"] or 0)
            total += amount
            boq_rows.append([
                safe_text(row.get("item")),
                safe_text(row.get("description"))[:180],
                safe_text(row.get("unit")),
                f"{float(row['quantity'] or 0):,.3f}",
                money(row["rate"]),
                money(amount),
                safe_text(row.get("priority"))
            ])

        boq_rows.append(["", "TOTAL ESTIMATED REPAIR COST", "", "", "",
                         money(total), ""])

        table = Table(boq_rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24476B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")
        ]))
        story.extend([table, Spacer(1, 5 * mm)])

    story.append(Paragraph("5. Engineering Limitations", styles["Heading2"]))
    story.append(Paragraph(
        "This report summarises field entries and preliminary cost estimates. "
        "It is not a structural safety certificate. Defect severity and "
        "repair decisions must be verified by a qualified structural engineer. "
        "Where safety is in doubt, restrict access and obtain an urgent "
        "professional assessment. Structural tests must be selected and "
        "interpreted by competent professionals.",
        styles["Normal"]
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# NAVIGATION
# ============================================================

pages = [
    "Dashboard",
    "Building Register",
    "Defect Survey",
    "Testing Register",
    "Repair BOQ",
    "Reports & Export"
]

page = st.sidebar.radio("Navigation", pages)

# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":
    st.header("Campus Condition Dashboard")

    buildings_df = get_buildings()
    defects_df = read_table("defects")
    tests_df = read_table("tests")
    boq_df = read_table("boq")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Buildings", len(buildings_df))
    c2.metric("Recorded Defects", len(defects_df))
    c3.metric("Tests / Investigations", len(tests_df))

    total_boq = (
        (boq_df["quantity"] * boq_df["rate"]).sum()
        if not boq_df.empty else 0
    )
    c4.metric("Preliminary Repair Estimate", money(total_boq))

    st.subheader("Defects by Severity")

    if defects_df.empty:
        st.info("No defect records yet. Add a building and record defects.")
    else:
        severity_counts = (
            defects_df["severity"].fillna("Unclassified")
            .value_counts()
        )
        st.bar_chart(severity_counts)

        st.subheader("Urgent Defects")
        urgent = defects_df[
            defects_df["urgency"].isin(
                ["Immediate", "Urgent", "High"]
            )
        ]

        if urgent.empty:
            st.info("No defects marked with urgent priority.")
        else:
            st.dataframe(
                urgent[[
                    "id", "building_id", "floor", "room",
                    "element", "defect_type", "severity",
                    "urgency", "status"
                ]],
                use_container_width=True,
                hide_index=True
            )

    st.warning(
        "Do not rely on this dashboard alone to determine whether a "
        "building is safe for occupation."
    )

# ============================================================
# BUILDING REGISTER
# ============================================================

elif page == "Building Register":
    st.header("Building Register")

    with st.form("building_form", clear_on_submit=True):
        name = st.text_input("Building name *")
        campus = st.text_input("Campus / department")
        address = st.text_input("Address / location")
        col1, col2, col3 = st.columns(3)

        with col1:
            year_built = st.number_input(
                "Year constructed", min_value=1900,
                max_value=date.today().year, value=2000
            )
        with col2:
            storeys = st.number_input(
                "Number of storeys", min_value=1,
                max_value=100, value=3
            )
        with col3:
            structural_system = st.selectbox(
                "Structural system",
                ["RCC framed", "Load-bearing masonry",
                 "Steel framed", "Composite", "Other / unknown"]
            )

        inspected_by = st.text_input("Inspector / survey team")
        inspection_date = st.date_input(
            "Inspection date", value=date.today()
        )
        notes = st.text_area("General building observations")

        submitted = st.form_submit_button("Save Building")

        if submitted:
            if not name.strip():
                st.error("Building name is required.")
            else:
                execute_sql("""
                    INSERT INTO buildings
                    (name, campus, address, year_built, storeys,
                     structural_system, inspected_by,
                     inspection_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name.strip(), campus, address, int(year_built),
                    int(storeys), structural_system, inspected_by,
                    str(inspection_date), notes
                ))
                st.success("Building record saved.")
                st.rerun()

    st.subheader("Existing Buildings")
    st.dataframe(get_buildings(), use_container_width=True, hide_index=True)

    if not buildings.empty:
        st.subheader("Delete a Building")
        st.warning(
            "Deleting a building also deletes its linked defects, tests "
            "and BOQ items. Export a backup first."
        )
        delete_id = st.selectbox(
            "Building to delete",
            buildings["id"].astype(int).tolist(),
            format_func=lambda x: building_label(
                buildings[buildings["id"] == x].iloc[0]
            )
        )

        confirm_delete = st.checkbox("Confirm permanent deletion")
        if st.button("Delete Selected Building", type="secondary"):
            if confirm_delete:
                execute_sql("DELETE FROM buildings WHERE id = ?", (delete_id,))
                st.success("Building and linked records deleted.")
                st.rerun()
            else:
                st.error("Tick the confirmation box before deleting.")

# ============================================================
# DEFECT SURVEY
# ============================================================

elif page == "Defect Survey":
    st.header("Field Defect Survey")

    if selected_building_id is None:
        st.info("Create a building record first.")
    else:
        st.caption(
            "Record observable conditions. Do not assign structural "
            "capacity or certify safety from visual observations alone."
        )

        with st.form("defect_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                floor = st.text_input("Floor / level", "Ground floor")
                room = st.text_input("Room / grid / zone")
                element = st.selectbox(
                    "Structural / building element",
                    [
                        "Column", "Beam", "Slab", "Foundation",
                        "Beam-column joint", "Staircase",
                        "Masonry wall", "Plaster", "Roof / terrace",
                        "Waterproofing", "Drainage", "Other"
                    ]
                )

            with col2:
                defect_type = st.selectbox(
                    "Observed defect",
                    [
                        "Crack", "Concrete spalling",
                        "Exposed reinforcement", "Reinforcement corrosion",
                        "Dampness / seepage", "Water leakage",
                        "Honeycombing", "Delamination",
                        "Settlement indication", "Deflection indication",
                        "Plaster deterioration", "Paint deterioration",
                        "Joint deterioration", "Other"
                    ]
                )

                severity = st.selectbox(
                    "Preliminary condition rating",
                    ["Minor", "Moderate", "Severe", "Critical", "Unassessed"]
                )

                urgency = st.selectbox(
                    "Recommended response priority",
                    ["Routine", "Planned", "High", "Urgent", "Immediate"]
                )

            with col3:
                length_m = st.number_input(
                    "Observed length (m)", min_value=0.0,
                    value=0.0, step=0.1
                )
                width_mm = st.number_input(
                    "Crack / defect width (mm)",
                    min_value=0.0, value=0.0, step=0.1
                )
                area_m2 = st.number_input(
                    "Affected area (m²)", min_value=0.0,
                    value=0.0, step=0.1
                )
                quantity = st.number_input(
                    "Measured quantity (if applicable)",
                    min_value=0.0, value=0.0, step=0.1
                )

            location_detail = st.text_input(
                "Exact location / grid reference"
            )
            observation = st.text_area(
                "Observed condition, dimensions and evidence"
            )
            recommended_action = st.text_area(
                "Proposed action / further assessment required"
            )

            photo = st.file_uploader(
                "Upload defect photograph",
                type=["jpg", "jpeg", "png", "webp"]
            )

            status = st.selectbox(
                "Record status",
                ["Open", "Under investigation", "Repair planned",
                 "Repaired", "Verified / closed"]
            )

            inspection_date = st.date_input(
                "Observation date", value=date.today()
            )

            submitted = st.form_submit_button("Save Defect")

            if submitted:
                photo_path = save_uploaded_photo(photo)

                execute_sql("""
                    INSERT INTO defects (
                        building_id, floor, room, element, defect_type,
                        severity, location_detail, length_m, width_mm,
                        area_m2, quantity, observation,
                        recommended_action, urgency, photo_path,
                        status, inspection_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    selected_building_id, floor, room, element,
                    defect_type, severity, location_detail,
                    length_m, width_mm, area_m2, quantity,
                    observation, recommended_action, urgency,
                    photo_path, status, str(inspection_date)
                ))
                st.success("Defect record saved.")
                st.rerun()

        st.subheader("Recorded Defects")
        defect_df = read_table("defects", selected_building_id)
        st.dataframe(defect_df, use_container_width=True, hide_index=True)

        if not defect_df.empty:
            defect_id = st.selectbox(
                "View defect photograph / details",
                defect_df["id"].astype(int).tolist(),
                key="defect_view"
            )
            selected_defect = defect_df[
                defect_df["id"] == defect_id
            ].iloc[0]

            if selected_defect["photo_path"]:
                if os.path.exists(selected_defect["photo_path"]):
                    st.image(
                        selected_defect["photo_path"],
                        caption=f"Defect ID {defect_id}",
                        width=500
                    )

            st.write("**Observation:**", selected_defect["observation"])
            st.write(
                "**Recommended action:**",
                selected_defect["recommended_action"]
            )

# ============================================================
# TESTING REGISTER
# ============================================================

elif page == "Testing Register":
    st.header("Investigation and Testing Register")

    if selected_building_id is None:
        st.info("Create a building record first.")
    else:
        with st.form("test_form", clear_on_submit=True):
            location = st.text_input("Test location / grid / floor")
            element = st.selectbox(
                "Element",
                ["Column", "Beam", "Slab", "Foundation",
                 "Beam-column joint", "Masonry", "Whole building", "Other"]
            )

            test_name = st.selectbox(
                "Investigation / test",
                [
                    "Detailed visual inspection",
                    "Crack mapping and monitoring",
                    "Rebound hammer test",
                    "Ultrasonic pulse velocity (UPV)",
                    "Reinforcement locator / cover meter",
                    "Carbonation depth test",
                    "Half-cell potential survey",
                    "Concrete core test",
                    "Chemical analysis of concrete",
                    "Steel reinforcement assessment",
                    "Foundation / settlement investigation",
                    "Level survey / deflection measurement",
                    "Load test (engineer-designed only)",
                    "Masonry investigation",
                    "Waterproofing investigation",
                    "Other / specialist test"
                ]
            )

            purpose = st.text_area("Purpose / reason for investigation")
            test_status = st.selectbox(
                "Status",
                ["Proposed", "Approved", "Scheduled",
                 "Completed", "Results reviewed", "Not required"]
            )
            result = st.text_area("Result / measured values")
            recommendation = st.text_area(
                "Interpretation / recommended next step"
            )
            test_date = st.date_input("Test date", value=date.today())
            cost = st.number_input(
                "Estimated / actual cost (INR)",
                min_value=0.0, value=0.0, step=500.0
            )

            submitted = st.form_submit_button("Save Test Record")

            if submitted:
                execute_sql("""
                    INSERT INTO tests (
                        building_id, location, element, test_name,
                        purpose, status, result, recommendation,
                        test_date, cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    selected_building_id, location, element,
                    test_name, purpose, test_status, result,
                    recommendation, str(test_date), cost
                ))
                st.success("Test record saved.")
                st.rerun()

        st.subheader("Investigation History")
        st.dataframe(
            read_table("tests", selected_building_id),
            use_container_width=True,
            hide_index=True
        )

        st.info(
            "Select tests based on the observed distress and the engineer's "
            "investigation plan. Rebound hammer and UPV results alone do not "
            "establish the in-situ compressive strength of concrete."
        )

# ============================================================
# REPAIR BOQ
# ============================================================

elif page == "Repair BOQ":
    st.header("Repair Bill of Quantities (BOQ)")

    if selected_building_id is None:
        st.info("Create a building record first.")
    else:
        st.caption(
            "Enter measured quantities and locally verified rates. "
            "Do not estimate structural repair quantities from photographs alone."
        )

        with st.form("boq_form", clear_on_submit=True):
            item = st.text_input("Item number / reference")
            description = st.text_input(
                "Repair / maintenance work description"
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                unit = st.selectbox(
                    "Unit", ["m", "m²", "m³", "kg", "number",
                             "lot", "L", "point", "day"]
                )
            with col2:
                quantity = st.number_input(
                    "Measured quantity", min_value=0.0,
                    value=0.0, step=0.1
                )
            with col3:
                rate = st.number_input(
                    "Rate (INR per unit)", min_value=0.0,
                    value=0.0, step=100.0
                )

            priority = st.selectbox(
                "Priority", ["Immediate", "Urgent", "High",
                             "Planned", "Routine"]
            )
            notes = st.text_area(
                "Measurement basis, specifications and assumptions"
            )

            submitted = st.form_submit_button("Add BOQ Item")

            if submitted:
                if not description.strip():
                    st.error("Enter a work description.")
                else:
                    execute_sql("""
                        INSERT INTO boq (
                            building_id, item, description, unit,
                            quantity, rate, priority, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        selected_building_id, item, description, unit,
                        quantity, rate, priority, notes
                    ))
                    st.success("BOQ item saved.")
                    st.rerun()

        boq_df = read_table("boq", selected_building_id)

        if boq_df.empty:
            st.info("No BOQ items have been entered.")
        else:
            boq_df["amount_INR"] = boq_df["quantity"] * boq_df["rate"]

            st.dataframe(
                boq_df, use_container_width=True, hide_index=True
            )

            total = boq_df["amount_INR"].sum()
            st.metric("Total Preliminary Repair Estimate", money(total))

            st.caption(
                "This total excludes any costs not entered in the BOQ, "
                "such as taxes, professional fees, access equipment, "
                "contingencies or hidden damage."
            )

# ============================================================
# REPORTS AND EXPORTS
# ============================================================

elif page == "Reports & Export":
    st.header("Reports and Data Export")

    report_scope = st.radio(
        "Report scope",
        ["Entire campus", "Selected building"],
        horizontal=True
    )

    if report_scope == "Selected building" and selected_building_id is None:
        st.warning("Create a building record first.")
    else:
        report_building_id = (
            selected_building_id
            if report_scope == "Selected building"
            else None
        )

        if st.button("Generate PDF Condition Report"):
            try:
                pdf_bytes = generate_pdf(report_building_id)
                st.download_button(
                    "Download PDF Report",
                    data=pdf_bytes,
                    file_name="campus_condition_report.pdf",
                    mime="application/pdf"
                )
            except Exception as error:
                st.error(f"Could not generate PDF: {error}")

    st.subheader("Export Survey Data")

    for table_name in ["buildings", "defects", "tests", "boq"]:
        df = (
            read_table(table_name, selected_building_id)
            if selected_building_id is not None
            and table_name != "buildings"
            else read_table(table_name)
        )

        st.download_button(
            label=f"Download {table_name.capitalize()} CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{table_name}_export.csv",
            mime="text/csv",
            key=f"download_{table_name}"
        )

    st.subheader("Local Data Backup")
    st.warning(
        "The database and photographs are stored on the computer running "
        "this app. Copy campus_survey.db and the survey_photos folder "
        "to a secure backup location."
    )

    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button(
                "Download SQLite Database Backup",
                data=file.read(),
                file_name="campus_survey_backup.db",
                mime="application/octet-stream"
            )

st.sidebar.markdown("---")
st.sidebar.caption(
    "For engineering use: validate observations, measurements, "
    "test interpretations and repair specifications before approval."
)
