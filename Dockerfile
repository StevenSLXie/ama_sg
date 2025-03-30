RUN pip install --no-cache-dir -r requirements.txt
RUN hayhooks pipeline deploy-files -n my_pipeline ./
