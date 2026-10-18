
from preprocessing import preprocess_transcript

transcript = """
sriya: okay guys we need to finish the dashboard.
rahul: i'll handle the API integration.
ananya: testing is blocked because login isn't working.
"""

results = preprocess_transcript(transcript)

for item in results:
    print(item)
