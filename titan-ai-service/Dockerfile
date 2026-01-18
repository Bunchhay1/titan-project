# ប្រើ Python Image តូចនិងស្រាល
FROM python:3.9-slim

# កំណត់កន្លែងធ្វើការក្នុង Container
WORKDIR /app

# Copy កូដទាំងអស់ពី Folder នេះចូលទៅក្នុង Container
COPY . .

# Install Library ដែលចាំបាច់ (បន្ថែមតាមតម្រូវការ)
# យើងដាក់ grpcio, flask, requests ព្រោះគម្រោងនេះទំនងជាត្រូវការវា
RUN pip install --no-cache-dir grpcio grpcio-tools requests flask

# បញ្ជាឱ្យ Run Python Script របស់អ្នក
CMD ["python", "main.py"]
