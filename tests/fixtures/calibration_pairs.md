# Calibration Pairs for podq Similarity Scoring

NOTE: These are synthetic pairs generated for initial testing. Real calibration should
use actual German podcast question pairs from the podcaster's archive (see open-questions.md).
LLM-generated paraphrases may inflate similarity scores vs. real diverse speaker phrasing.

## Paraphrase Pairs (should score >= 0.80 similarity)

1. "Wie oft sollte man Sport machen?" / "Wie viele Male pro Woche empfiehlt sich Training?"
   - Expected: >= 0.80 (asking the same question about exercise frequency)

2. "Was ist das beste Mittel gegen Erkältung?" / "Welche Hausmittel helfen bei Schnupfen?"
   - Expected: >= 0.70 (similar topic, slight variation — may need threshold=0.70)

3. "Können Sie Bücher über Meditation empfehlen?" / "Welche Bücher zum Thema Achtsamkeit empfehlen Sie?"
   - Expected: >= 0.75

4. "Wie lerne ich besser Fremdsprachen?" / "Was sind gute Methoden um Sprachen zu lernen?"
   - Expected: >= 0.78

5. "Was denken Sie über vegane Ernährung?" / "Wie stehen Sie zur veganen Lebensweise?"
   - Expected: >= 0.80

## Unrelated Pairs (should score < 0.80 similarity)

1. "Was ist das beste Mittel gegen Erkältung?" / "Wie repariere ich mein Fahrrad?"
   - Expected: < 0.40

2. "Können Sie Bücher über Meditation empfehlen?" / "Welche Aktien sollte ich kaufen?"
   - Expected: < 0.30

3. "Wie oft sollte man Sport machen?" / "Was koche ich heute Abend?"
   - Expected: < 0.35

4. "Wie lerne ich besser Fremdsprachen?" / "Wo kaufe ich am besten Elektronik?"
   - Expected: < 0.30

5. "Was denken Sie über vegane Ernährung?" / "Wie funktioniert ein Elektromotor?"
   - Expected: < 0.25

## Notes
- Default threshold: 0.80 (may need to lower to 0.70 for borderline pairs after real-data calibration)
- Model: paraphrase-multilingual-MiniLM-L12-v2
- Real calibration date: TBD (pending access to podcaster archive)
