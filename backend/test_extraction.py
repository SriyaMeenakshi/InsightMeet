
from preprocessing import preprocess_transcript
from extraction import extract_information

transcript = """
Sriya: We need to finish the dashboard by Friday.
Rahul: I'll fix the login issue tomorrow.
Ananya: The API is failing.
Sriya: Let's use SQLite for now.
Kiran: Maybe we should try another database.
"""

processed = preprocess_transcript(transcript)
results = extract_information(processed)

for section, items in results.items():
    print(f"\n{section.upper()}")

    for item in items:
        print(item)
