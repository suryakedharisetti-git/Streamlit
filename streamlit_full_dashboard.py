{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 38,
   "id": "3a8bb328",
   "metadata": {},
   "outputs": [],
   "source": [
    "from fastapi import FastAPI, HTTPException, Depends, Request, Query, Form\n",
    "from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse\n",
    "from fastapi.templating import Jinja2Templates\n",
    "from fastapi.security.api_key import APIKeyHeader\n",
    "from pymongo import MongoClient, errors\n",
    "from pydantic import BaseModel\n",
    "from bson import ObjectId\n",
    "import pandas as pd\n",
    "import io\n",
    "from datetime import datetime"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 39,
   "id": "5505e842",
   "metadata": {},
   "outputs": [],
   "source": [
    "app = FastAPI()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 40,
   "id": "3500d535",
   "metadata": {},
   "outputs": [],
   "source": [
    "client = MongoClient(\"mongodb://localhost:27017/\")\n",
    "db = client[\"fastapi_db\"]"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 41,
   "id": "f1470fa6",
   "metadata": {},
   "outputs": [],
   "source": [
    "try:\n",
    "    db.students.create_index(\"email\", unique=True)\n",
    "except errors.DuplicateKeyError:\n",
    "    print(\"Duplicate emails exist, index not created. Clean data before retrying.\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 42,
   "id": "9c67b355",
   "metadata": {},
   "outputs": [],
   "source": [
    "def clean_document(doc):\n",
    "    doc[\"_id\"] = str(doc[\"_id\"])\n",
    "    return doc\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 43,
   "id": "70ed8b74",
   "metadata": {},
   "outputs": [],
   "source": [
    "class Student(BaseModel):\n",
    "    student_id: int\n",
    "    name: str\n",
    "    age: int\n",
    "    grade: str\n",
    "    email: str\n",
    "\n",
    "\n",
    "class Course(BaseModel):\n",
    "    course_id: int\n",
    "    course_name: str\n",
    "\n",
    "\n",
    "class Enrollment(BaseModel):\n",
    "    student_id: int\n",
    "    course_id: int"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 44,
   "id": "1d4dd639",
   "metadata": {},
   "outputs": [],
   "source": [
    "@app.post(\"/students\")\n",
    "def create_student(student: Student):\n",
    "    try:\n",
    "        student_dict = student.model_dump()\n",
    "        result = db.students.insert_one(student_dict)\n",
    "        return {\"inserted_id\": str(result.inserted_id)}\n",
    "    except errors.DuplicateKeyError:\n",
    "        return JSONResponse(status_code=409, content={\"detail\": \"Email already exists\"})\n",
    "\n",
    "\n",
    "@app.get(\"/students\")\n",
    "def get_students():\n",
    "    students = list(db.students.find())\n",
    "    return [clean_document(s) for s in students]\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 45,
   "id": "08d28dd8",
   "metadata": {},
   "outputs": [],
   "source": [
    "@app.get(\"/students/paginated\")\n",
    "def paginated_students(page: int = Query(1, ge=1), limit: int = Query(10, ge=1)):\n",
    "    skip = (page - 1) * limit\n",
    "    students = list(db.students.find().skip(skip).limit(limit))\n",
    "    return [clean_document(s) for s in students]\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 46,
   "id": "3e36ad76",
   "metadata": {},
   "outputs": [
    {
     "name": "stderr",
     "output_type": "stream",
     "text": [
      "C:\\Users\\surya\\AppData\\Local\\Temp\\ipykernel_20536\\3130761129.py:4: DeprecationWarning: `regex` has been deprecated, please use `pattern` instead\n",
      "  sort: str = Query(\"asc\", regex=\"^(asc|desc)$\", description=\"Sort order (asc/desc)\"),\n"
     ]
    }
   ],
   "source": [
    "@app.get(\"/students/filter\")\n",
    "def filter_students(\n",
    "    min_age: int = Query(0, ge=0, description=\"Minimum age filter\"),\n",
    "    sort: str = Query(\"asc\", regex=\"^(asc|desc)$\", description=\"Sort order (asc/desc)\"),\n",
    "):\n",
    "    sort_order = 1 if sort == \"asc\" else -1\n",
    "    students = list(\n",
    "        db.students.find({\"age\": {\"$gte\": min_age}}).sort(\"age\", sort_order)\n",
    "    )\n",
    "    return [clean_document(s) for s in students]\n",
    "\n",
    "\n",
    "@app.get(\"/students/{student_id}\")\n",
    "def get_student(student_id: int):\n",
    "    student = db.students.find_one({\"student_id\": student_id})\n",
    "    return clean_document(student) if student else {\"detail\": \"Not found\"}\n",
    "\n",
    "\n",
    "@app.put(\"/students/{student_id}\")\n",
    "def update_student(student_id: int, student: Student):\n",
    "    update_data = student.model_dump(exclude_unset=True)\n",
    "    db.students.update_one({\"student_id\": student_id}, {\"$set\": update_data})\n",
    "    return {\"message\": \"Student updated\"}\n",
    "\n",
    "\n",
    "@app.delete(\"/students/{student_id}\")\n",
    "def delete_student(student_id: int):\n",
    "    if db.enrollments.find_one({\"student_id\": student_id}):\n",
    "        return {\"detail\": \"Student is enrolled in a course\"}\n",
    "    db.students.delete_one({\"student_id\": student_id})\n",
    "    return {\"message\": \"Student deleted\"}"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 47,
   "id": "a69658db",
   "metadata": {},
   "outputs": [],
   "source": [
    "@app.post(\"./courses.csv\")\n",
    "def create_course(course: Course):\n",
    "    result = db.courses.insert_one(course.model_dump())\n",
    "    return {\"inserted_id\": str(result.inserted_id)}\n",
    "\n",
    "\n",
    "@app.get(\"./courses.csv\")\n",
    "def get_courses():\n",
    "    return [clean_document(c) for c in db.courses.find()]\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 48,
   "id": "cb71feba",
   "metadata": {},
   "outputs": [],
   "source": [
    "@app.post(\"./enrollments.csv\")\n",
    "def enroll_student(enrollment: Enrollment):\n",
    "    result = db.enrollments.insert_one(enrollment.model_dump())\n",
    "    return {\"inserted_id\": str(result.inserted_id)}\n",
    "\n",
    "\n",
    "@app.get(\"./enrollments.csv\")\n",
    "def get_enrollments():\n",
    "    return [clean_document(e) for e in db.enrollments.find()]\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 49,
   "id": "de598530",
   "metadata": {},
   "outputs": [],
   "source": [
    "@app.get(\"/stats/grades\")\n",
    "def grade_stats():\n",
    "    pipeline = [{\"group\": {\"_id\": \"grade\", \"count\": {\"sum\": 1}}}]\n",
    "    return {doc[\"_id\"]: doc[\"count\"] for doc in db.students.aggregate(pipeline)}\n",
    "\n",
    "\n",
    "@app.get(\"/stats/top-courses\")\n",
    "def top_courses():\n",
    "    pipeline = [\n",
    "        {\"group\": {\"_id\": \"course_id\", \"count\": {\"sum\": 1}}},\n",
    "        {\"sort\": {\"count\": -1}},\n",
    "    ]\n",
    "    return list(db.enrollments.aggregate(pipeline))\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 50,
   "id": "9773e502",
   "metadata": {},
   "outputs": [],
   "source": [
    "@app.post(\"/upload-csv\")\n",
    "async def upload_csv(file: bytes):\n",
    "    df = pd.read_csv(io.BytesIO(file))\n",
    "    db.students.insert_many(df.to_dict(orient=\"records\"))\n",
    "    return {\"message\": \"CSV uploaded\"}\n",
    "@app.get(\"/students/export\")\n",
    "def export_students():\n",
    "    students = list(db.students.find())\n",
    "    df = pd.DataFrame(students)\n",
    "    df[\"_id\"] = df[\"_id\"].astype(str)\n",
    "    stream = io.StringIO()\n",
    "    df.to_csv(stream, index=False)\n",
    "    response = StreamingResponse(iter([stream.getvalue()]), media_type=\"text/csv\")\n",
    "    response.headers[\"Content-Disposition\"] = \"attachment; filename=students.csv\"\n",
    "    return response\n",
    "\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "9c303826",
   "metadata": {},
   "outputs": [],
   "source": [
    "client = MongoClient(\"mongodb://localhost:27017/\")\n",
    "db = client[\"mydatabase\"]\n",
    "students_collection = db[\"students\"]\n",
    "\n",
    "@app.post(\"/upload-csv\")\n",
    "async def upload_csv(file: UploadFile = File(...)):\n",
    "    # Check file type\n",
    "    if not file.filename.endswith(\".csv\"):\n",
    "        raise HTTPException(status_code=400, detail=\"Only CSV files are allowed\")\n",
    "\n",
    "    try:\n",
    "        # Read file contents\n",
    "        content = await file.read()\n",
    "        df = pd.read_csv(io.BytesIO(content))\n",
    "\n",
    "        # Validate required columns\n",
    "        required_columns = {\"name\", \"age\", \"grade\", \"email\"}\n",
    "        if not required_columns.issubset(df.columns):\n",
    "            raise HTTPException(\n",
    "                status_code=400,\n",
    "                detail=f\"CSV must contain columns: {', '.join(required_columns)}\"\n",
    "            )\n",
    "\n",
    "        # Convert DataFrame to dictionary list\n",
    "        records = df.to_dict(orient=\"records\")\n",
    "\n",
    "        # Insert into MongoDB\n",
    "        if records:\n",
    "            students_collection.insert_many(records)\n",
    "\n",
    "        return {\"message\": f\"Inserted {len(records)} students successfully\"}\n",
    "\n",
    "    except Exception as e:\n",
    "        raise HTTPException(status_code=500, detail=f\"Error processing file: {str(e)}\")\n",
    "\n",
    "\n",
    "@app.get(\"/upload-csv\")\n",
    "def upload_csv_info():\n",
    "    return {\"message\": \"Use POST /upload-csv with a CSV file to upload students\"}\n"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.13.2"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
