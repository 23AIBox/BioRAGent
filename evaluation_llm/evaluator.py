import csv
def evaluate_csv(dataset_file: str, output_file: str,model_fn):
   
    encodings_to_try = ['utf-8', 'latin-1', 'ISO-8859-1', 'Windows-1252']

    for encoding in encodings_to_try:
        try:
            with open(dataset_file, 'r', encoding=encoding) as csvfile, \
                 open(output_file, 'w', newline='', encoding="utf-8") as outputcsvfile:
                reader = csv.reader(csvfile)
                writer = csv.writer(outputcsvfile)
                writer.writerow(['Question', 'Standard Answer', 'Agent Answer'])

                next(reader, None)  

                for row in reader:
                    row = [item.strip() for item in row if item.strip()]
                    if len(row) == 2:
                        question = row[0]
                        standard_answer = row[1]

                        try:
                            model_answer = model_fn(question).strip()
                        except Exception as model_error:
                            model_answer = f"[ERROR: {model_error}]"

                        writer.writerow([question, standard_answer, model_answer])
                        print(f"Q: {question}\nA: {model_answer}\n---")
            break
        except UnicodeDecodeError:
            print(f"Failed to decode using {encoding} encoding. Trying next encoding...")
            continue
        except Exception as e:
            print(f"An error occurred: {e}")
            break