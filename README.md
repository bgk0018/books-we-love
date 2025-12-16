## Books We Love – CLI Seeder

Simple Python 3 CLI that downloads NPR “Books We Love” JSON for selected years and saves them to a local `data` folder.

Source JSON looks like `https://apps.npr.org/best-books/2025.json` and similar for other years. See the example at [`https://apps.npr.org/best-books/2025.json`](https://apps.npr.org/best-books/2025.json).

### Setup (Windows / Python 3)

```bash
cd C:\src\books-we-love
py -3 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Usage

Run the seeder from the project root:

```bash
python -m books_we_love.cli seed --year 2025   # single year
python -m books_we_love.cli seed              # all years by algorithm
```

### Year selection algorithm

- Earliest year: **2013**
- Latest year:
  - If it is **December or later** in the current year, include the **current year**.
  - Otherwise, include **up to last year**.

For example, in December 2025 this will download 2013–2025.


