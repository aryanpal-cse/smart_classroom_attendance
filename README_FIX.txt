SMART CLASSROOM MINI PROJECT — SAMPLE CAP AND SCORE LABEL FIX

Changes:
1. Face registration stops accepting samples after the configured target.
2. Student and Admin pages never display more than the configured target (for example, 10/10 instead of 11/10).
3. The attendance result now says "Face-match score" instead of "Prototype similarity score".
4. Existing databases and face_data folders are not replaced.

Apply by extracting this ZIP into the project root with overwrite enabled.
Then run:
    python -m py_compile routes\student.py routes\admin.py
    python -m unittest discover -s tests -v
