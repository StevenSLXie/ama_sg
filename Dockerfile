# Use a lightweight Python image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy project files
COPY . .

RUN pip install --no-cache-dir -r requirements.txt
# RUN hayhooks pipeline deploy-files -n my_pipeline ./

# Expose the port Hayhooks runs on
EXPOSE 1416

# Run Hayhooks
CMD ["hayhooks", "serve"]