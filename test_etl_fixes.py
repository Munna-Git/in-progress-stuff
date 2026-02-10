"""
Quick test script to verify ETL extractor and normalizer fixes.
Tests 3-level header detection and bi-amp power parsing.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_extractor():
    """Test the extractor with the Bose PDF."""
    from src.etl.extractor import PDFExtractor
    
    pdf_path = Path("./Bose-Products 3.pdf")
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return None
    
    extractor = PDFExtractor()
    extractor.clear_cache()  # Force fresh extraction
    
    print("Running extraction...")
    result = await extractor.extract(pdf_path, force_refresh=True)
    
    print(f"\n=== Extraction Results ===")
    print(f"Total pages: {result.total_pages}")
    print(f"Tables extracted: {len(result.tables)}")
    
    # Check for ArenaMatch table (page 9)
    arenamatch_found = False
    for table in result.tables:
        if table.page_number == 9:
            arenamatch_found = True
            print(f"\n=== Page 9 (ArenaMatch) Table ===")
            print(f"Headers: {table.headers[:5]}...")  # First 5 headers
            print(f"Rows: {len(table.rows)}")
            if table.rows:
                print(f"First row keys: {list(table.rows[0].keys())[:5]}")
    
    if not arenamatch_found:
        print("WARNING: Page 9 (ArenaMatch) table not found!")
    
    return result


async def test_normalizer(extraction_result):
    """Test the normalizer with extracted data."""
    from src.etl.normalizer import ProductNormalizer
    
    if not extraction_result:
        print("No extraction result to normalize")
        return
    
    normalizer = ProductNormalizer()
    
    print("\nRunning normalization...")
    result = await normalizer.normalize([extraction_result.to_dict()])
    
    print(f"\n=== Normalization Results ===")
    print(f"Total products: {len(result.products)}")
    print(f"Stats: {result.stats}")
    
    # Check for bi-amp power parsing
    biamp_products = []
    for p in result.products:
        if 'power_biamp_lf_watts' in p.specs or 'power_passive_watts' in p.specs:
            biamp_products.append(p)
    
    print(f"\nProducts with bi-amp/passive power: {len(biamp_products)}")
    if biamp_products:
        sample = biamp_products[0]
        print(f"Sample: {sample.model_name}")
        print(f"  Specs: {sample.specs}")
    
    # Look for ArenaMatch products
    am_products = [p for p in result.products if 'AM' in p.model_name.upper()]
    print(f"\nArenaMatch products: {len(am_products)}")
    if am_products:
        for p in am_products[:3]:
            print(f"  - {p.model_name}")


async def main():
    print("ETL Verification Test")
    print("=" * 50)
    
    result = await test_extractor()
    await test_normalizer(result)
    
    print("\n" + "=" * 50)
    print("Test completed.")


if __name__ == "__main__":
    asyncio.run(main())
