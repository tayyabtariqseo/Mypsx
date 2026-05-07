# Daily Portfolio Update Procedure

To update your account sale/purchase data daily, follow these steps:

### 1. Update Portfolio Files
The dashboard reads data from four text files in the root directory:
- `RSL.txt` (RAFI Account)
- `MMK.txt` (MMK Account)
- `SPK.txt` (SPK Account)
- `SFEL.txt` (SFEL Account)

### 2. File Format Rules
Each line in the text files must follow this exact format:
`SYMBOL [SPACE/TAB] QUANTITY [SPACE/TAB] AVERAGE_PRICE`

**Example:**
```text
SYS 1000 155.50
PSO 500 370.00
```

### 3. How to Update
- **Method A (GitHub Web):**
  1. Open your repository on GitHub.
  2. Click on the file you want to update (e.g., `SPK.txt`).
  3. Click the **Pencil icon** (Edit) and update your holdings.
  4. Click **Commit changes**. The dashboard will update automatically within 30 seconds.

- **Method B (Local Editor):**
  1. Open the file in Notepad.
  2. Update the values.
  3. Save and push to GitHub using Git Desktop or command line.

### 4. Special Symbols
- For Futures, you can use `PSO-MAY` or just `PSO`. The system will automatically fetch the correct underlying price.
- Ensure there are no extra symbols or currency marks (like "Rs.") inside the text files.
