# streamlit_full_dashboard.py

import streamlit as st
from pymongo import MongoClient
import pandas as pd
import plotly.express as px
import time
from bson.json_util import dumps


@st.cache_resource
def get_db_connection():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["school_db"]
    return db


db = get_db_connection()


@st.cache_data
def fetch_collection_data(collection_name):
    with st.spinner(f"Loading {collection_name} data from MongoDB..."):
        time.sleep(0.5)
        collection = db[collection_name]
        data = list(collection.find())
        return pd.DataFrame(data)


st.set_page_config(page_title="School Dashboard Full", layout="wide")
st.title("🎓 Full School Dashboard")

with st.form("login_form"):
    username = st.text_input("Enter your username")
    submitted = st.form_submit_button("Login")

if submitted and username:
    st.success(f"Hi, {username}! Welcome to your dashboard.")
else:
    st.info("Please enter your username to personalize the dashboard.")

students_df = fetch_collection_data("students")
courses_df = fetch_collection_data("courses")
enrollments_df = fetch_collection_data("enrollments")

for df in [students_df, courses_df, enrollments_df]:
    if "_id" in df.columns:
        df.drop(columns=["_id"], inplace=True)

st.sidebar.subheader("Dashboard Controls")

collection_choice = st.sidebar.selectbox(
    "Select Collection for Raw View", ["students", "courses", "enrollments"]
)
view_format = st.sidebar.radio("Select View Format", ["Table View", "JSON View"])


grades = (
    students_df["grade"].unique().tolist() if "grade" in students_df.columns else []
)
selected_grades = st.sidebar.multiselect(
    "Select Grade(s)", options=grades, default=grades
)

ages_min, ages_max = int(students_df["age"].min()), (
    int(students_df["age"].max()) if "age" in students_df.columns else (0, 100)
)
selected_age_range = st.sidebar.slider(
    "Select Age Range",
    min_value=ages_min,
    max_value=ages_max,
    value=(ages_min, ages_max),
)

courses = (
    enrollments_df["course_id"].unique().tolist()
    if "course_id" in enrollments_df.columns
    else []
)
selected_courses = st.sidebar.multiselect(
    "Select Course(s)", options=courses, default=courses
)

instructors = (
    enrollments_df["instructor"].unique().tolist()
    if "instructor" in enrollments_df.columns
    else []
)
selected_instructors = st.sidebar.multiselect(
    "Select Instructor(s)", options=instructors, default=instructors
)


filtered_students = students_df.copy()
if "grade" in filtered_students.columns:
    filtered_students = filtered_students[
        filtered_students["grade"].isin(selected_grades)
    ]
if "age" in filtered_students.columns:
    filtered_students = filtered_students[
        (filtered_students["age"] >= selected_age_range[0])
        & (filtered_students["age"] <= selected_age_range[1])
    ]

filtered_enrollments = enrollments_df.copy()
if "course_id" in filtered_enrollments.columns:
    filtered_enrollments = filtered_enrollments[
        filtered_enrollments["course_id"].isin(selected_courses)
    ]
if "instructor" in filtered_enrollments.columns:
    filtered_enrollments = filtered_enrollments[
        filtered_enrollments["instructor"].isin(selected_instructors)
    ]


st.subheader("📂 Raw Data View")
raw_data_df = fetch_collection_data(collection_choice)
if "_id" in raw_data_df.columns:
    raw_data_df.drop(columns=["_id"], inplace=True)

if view_format == "Table View":
    st.dataframe(raw_data_df.head(10))
    st.table(raw_data_df.head(10))
else:
    st.json(dumps(raw_data_df[:10], indent=2))


st.subheader("📈 Key Performance Indicators (KPIs)")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Students", len(students_df))
col2.metric("Total Courses", len(courses_df))
avg_age = round(students_df["age"].mean(), 1) if "age" in students_df.columns else "N/A"
col3.metric("Average Age", avg_age)
col4.metric("Enrollments Count", len(enrollments_df))


with st.expander("More Insights: Top 5 Courses"):
    if "course_id" in enrollments_df.columns:
        top_courses = enrollments_df["course_id"].value_counts().head(5)
        st.table(top_courses)

# -------------------- 9. Editable Student Data --------------------
st.subheader("📝 Edit Student Information")
if not filtered_students.empty:
    edited_students_df = st.data_editor(
        filtered_students, num_rows="dynamic", use_container_width=True
    )

    if not edited_students_df.equals(filtered_students):
        for index, row in edited_students_df.iterrows():
            db["students"].update_one(
                (
                    {"_id": students_df.iloc[index]["_id"]}
                    if "_id" in students_df.columns
                    else {"age": row["age"]}
                ),
                {"$set": row.to_dict()},
            )
        st.success("Student data updated successfully!")

# -------------------- 10. Advanced Visualizations --------------------
st.subheader("📊 Advanced Visualizations")
tab1, tab2, tab3 = st.tabs(
    ["Enrollment Trends", "Grade Distribution", "Course Popularity"]
)

with tab1:
    st.markdown("### Enrollment Trends Over Time")
    if "enrollment_date" in enrollments_df.columns:
        enrollments_df["enrollment_date"] = pd.to_datetime(
            enrollments_df["enrollment_date"]
        )
        trend_df = (
            enrollments_df.groupby("enrollment_date").size().reset_index(name="count")
        )
        trend_df = trend_df.sort_values("enrollment_date")
        st.line_chart(
            trend_df.rename(columns={"enrollment_date": "index"}).set_index("index")[
                "count"
            ]
        )
    else:
        st.info("No enrollment_date field available.")

with tab2:
    st.markdown("### Number of Students per Grade")
    if "grade" in students_df.columns:
        grade_count = students_df["grade"].value_counts()
        st.bar_chart(grade_count)
    else:
        st.info("No grade data available.")

with tab3:
    st.markdown("### Students by Course")
    if "course_id" in enrollments_df.columns:
        course_count = enrollments_df["course_id"].value_counts().reset_index()
        course_count.columns = ["course_id", "count"]
        fig = px.pie(course_count, names="course_id", values="count", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No course_id data available.")

# -------------------- 11. Download Filtered Students --------------------
if not filtered_students.empty:
    st.subheader("📥 Download Filtered Students")
    csv_data = filtered_students.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name="filtered_students.csv",
        mime="text/csv",
    )
