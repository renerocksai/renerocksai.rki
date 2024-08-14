FROM python:3.11-slim

WORKDIR /app

COPY datasets-release/Zusatzmaterial_RST_faiss.index /datasets/Zusatzmaterial_RST_faiss.index
COPY datasets-release/Zusatzmaterial_RST_metadata.pkl /datasets/Zusatzmaterial_RST_metadata.pkl
COPY datasets-release/Sitzungsprotokolle_RST_faiss.index /datasets/Sitzungsprotokolle_RST_faiss.index
COPY datasets-release/Sitzungsprotokolle_RST_metadata.pkl /datasets/Sitzungsprotokolle_RST_metadata.pkl
COPY datasets-release/corona-BKA_faiss.index /datasets/corona-BKA_faiss.index
COPY datasets-release/corona-BKA_metadata.pkl /datasets/corona-BKA_metadata.pkl
COPY datasets-release/corona-BMG_BMI_faiss.index /datasets/corona-BMG_BMI_faiss.index
COPY datasets-release/corona-BMG_BMI_metadata.pkl /datasets/corona-BMG_BMI_metadata.pkl
COPY datasets-release/corona-EXP_REGIERUNG_faiss.index /datasets/corona-EXP_REGIERUNG_faiss.index
COPY datasets-release/corona-EXP_REGIERUNG_metadata.pkl /datasets/corona-EXP_REGIERUNG_metadata.pkl
COPY datasets-release/corona-MPK_faiss.index /datasets/corona-MPK_faiss.index
COPY datasets-release/corona-MPK_metadata.pkl /datasets/corona-MPK_metadata.pkl
COPY datasets-release/corona_ALL_faiss.index /datasets/corona_ALL_faiss.index
COPY datasets-release/corona_ALL_metadata.pkl /datasets/corona_ALL_metadata.pkl
COPY datasets-release/corona_ABSOLUTELY_EVERYTHING_faiss.index /datasets/corona_ABSOLUTELY_EVERYTHING_faiss.index
COPY datasets-release/corona_ABSOLUTELY_EVERYTHING_metadata.pkl /datasets/corona_ABSOLUTELY_EVERYTHING_metadata.pkl

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
ENV RKI_DATASET_corona_BKA=corona-BKA
ENV RKI_DATASET_corona_BMG_BMI=corona-BMG_BMI
ENV RKI_DATASET_corona_EXP_REGIERUNG=corona-EXP_REGIERUNG
ENV RKI_DATASET_corona_MPK=corona-MPK
ENV RKI_DATASET_corona_ALL=corona_ALL
ENV RKI_DATASET_corona_ABSOLUTELY_EVERYTHING=corona_ABSOLUTELY_EVERYTHING

# Run app.py when the container launches
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "doubleapi:app", "--access-logfile", "/logs/api.access.log", "--error-logfile", "/logs/api.error.log"]

