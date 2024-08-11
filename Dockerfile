FROM python:3.11-slim

WORKDIR /app

COPY datasets-release/Zusatzmaterial_RST_faiss.index /datasets/Zusatzmaterial_RST_faiss.index
COPY datasets-release/Zusatzmaterial_RST_metadata.pkl /datasets/Zusatzmaterial_RST_metadata.pkl
COPY datasets-release/Sitzungsprotokolle_RST_faiss.index /datasets/Sitzungsprotokolle_RST_faiss.index
COPY datasets-release/Sitzungsprotokolle_RST_metadata.pkl /datasets/Sitzungsprotokolle_RST_metadata.pkl

COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the contents of the src/ directory to the working directory (/app)
COPY src/ .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variables
ENV FLASK_APP=doubleapi.py
ENV RKI_DATASETS_DIR=/datasets
ENV RKI_DATASET_sitzungsprotokolle=Sitzungsprotokolle_RST
ENV RKI_DATASET_zusatzmaterial=Zusatzmaterial_RST

# Run app.py when the container launches
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "doubleapi:app", "--access-logfile", "/logs/api.access.log", "--error-logfile", "/logs/api.error.log"]

