# This script is the main script for the AI-File-Manager project. It should be run from the command line and recieve an input file path from the user. It will then send a few snippets of the content, the file name, and any metadata to a free, fast AI model for processing (Groq). The AI model will then return a response which will be printed to the console with the following information:

# 1. One-sentence summary
# 2. Category
# 3. Importance (1–10)
# 4. Keep/Delete/Archive
# 5. Confidence (0–100%)
# 6. Reasoning
# 7. Suggested filename

# Output will be in Markdown format for easy reading and copying. The script will also save the AI response to a text file in the same directory as the input file, with the same name as the input file but with a .ai.txt extension.
# Output will later be turned into a GUI and the AI will be instructed to format in JSON strictly for easy parsing and integration with other systems.