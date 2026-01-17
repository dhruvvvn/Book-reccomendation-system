
import csv
import json
import gzip
import os
import random

INPUT_FILE = r'C:\Users\HP\Desktop\Book reccomendation sys\books.csv'
OUTPUT_FILE = r'C:\Users\HP\Desktop\Book reccomendation sys\backend\data\books_full.json'

def convert_csv_to_json():
    print(f"Reading from: {INPUT_FILE}")
    books = []
    
    # Genres to assign randomly since dataset lacks them (makes the demo more fun)
    GENRES = ["Fiction", "Mystery", "Sci-Fi", "Fantasy", "Romance", "History", "Thriller", "Biography", "Classic", "Horror"]
    
    try:
        # The dataset often uses ISO-8859-1 or cp1252
        with open(INPUT_FILE, mode='r', encoding='iso-8859-1') as f:
            # It uses semi-colons and quote-char "
            reader = csv.DictReader(f, delimiter=';', quotechar='"')
            
            count = 0
            for row in reader:
                # Keys in CSV: "ISBN","Book-Title","Book-Author","Year-Of-Publication","Publisher","Image-URL-S","Image-URL-M","Image-URL-L"
                
                try:
                    book = {
                        "id": row.get("ISBN", ""),
                        "title": row.get("Book-Title", ""),
                        "author": row.get("Book-Author", ""),
                        "description": f"Published by {row.get('Publisher', 'Unknown')} in {row.get('Year-Of-Publication', 'Unknown')}.", # Placeholder description
                        "genre": random.choice(GENRES), # Placeholder
                        "cover_url": row.get("Image-URL-L", ""), # Use Large image
                        "rating": float(random.randint(30, 50)) / 10.0 # Placeholder random rating 3.0-5.0
                    }
                    
                    if book["id"] and book["title"]:
                        books.append(book)
                        count += 1
                        
                    if count % 10000 == 0:
                        print(f"Processed {count} books...")
                        
                except Exception as e:
                    continue

        print(f"Total valid books processed: {len(books)}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(books, f, indent=2)
            
        print(f"Successfully saved to {OUTPUT_FILE}")
        
    except FileNotFoundError:
        print(f"Error: Could not find {INPUT_FILE}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    convert_csv_to_json()
