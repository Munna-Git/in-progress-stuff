<frozen runpy>:128: RuntimeWarning: 'src.etl.pipeline' found in sys.modules after import of package 'src.etl', but prior to execution of 'src.etl.pipeline'; this may result in unpredictable behaviour
2026-02-12 12:34:39,411 - __main__ - INFO - Starting ETL pipeline - Job ID: b6e412d4-0e7c-4e69-a286-4ff9038e0001
2026-02-12 12:34:39,411 - __main__ - INFO - PDF directory: D:\production local RAG\data\raw_pdfs
2026-02-12 12:34:39,411 - src.database - INFO - Initializing database pool: localhost:5433/bose_products
2026-02-12 12:34:39,994 - src.database - INFO - Database pool initialized with 2-10 connections
2026-02-12 12:34:40,110 - __main__ - INFO - Stage 1: Extraction
2026-02-12 12:34:40,112 - __main__ - INFO - Force refresh enabled - clearing extraction cache
2026-02-12 12:34:40,117 - src.etl.extractor - INFO - Cleared all cache files in D:\production local RAG\data\processed
2026-02-12 12:34:40,119 - src.etl.extractor - INFO - Found 1 PDF files to process
2026-02-12 12:34:40,120 - src.etl.extractor - INFO - Extracting tables from: D:\production local RAG\data\raw_pdfs\Bose-Products 3.pdf
2026-02-12 12:36:13,237 - src.etl.extractor - INFO - Running docling conversion on Bose-Products 3.pdf...
2026-02-12 12:36:13,279 - docling.datamodel.document - INFO - detected formats: [<InputFormat.PDF: 'pdf'>]
2026-02-12 12:36:17,840 - docling.document_converter - INFO - Going to convert document batch...
2026-02-12 12:36:17,845 - docling.document_converter - INFO - Initializing pipeline for StandardPdfPipeline with options hash 51708fa6c91477fa58d917b4cbfd8799
2026-02-12 12:36:17,906 - docling.models.factories.base_factory - INFO - Loading plugin 'docling_defaults'
2026-02-12 12:36:17,923 - docling.models.factories - INFO - Registered picture descriptions: ['vlm', 'api']
2026-02-12 12:36:17,968 - docling.models.factories.base_factory - INFO - Loading plugin 'docling_defaults'
2026-02-12 12:36:17,999 - docling.models.factories - INFO - Registered ocr engines: ['auto', 'easyocr', 'ocrmac', 'rapidocr', 'tesserocr', 'tesseract']
2026-02-12 12:36:18,403 - docling.models.factories.base_factory - INFO - Loading plugin 'docling_defaults'
2026-02-12 12:36:18,425 - docling.models.factories - INFO - Registered layout engines: ['docling_layout_default', 'docling_experimental_table_crops_layout']
2026-02-12 12:36:18,456 - docling.utils.accelerator_utils - INFO - Accelerator device: 'cpu'
2026-02-12 12:36:24,692 - docling.models.factories.base_factory - INFO - Loading plugin 'docling_defaults'
2026-02-12 12:36:24,700 - docling.models.factories - INFO - Registered table structure engines: ['docling_tableformer']
2026-02-12 12:36:25,621 - docling.utils.accelerator_utils - INFO - Accelerator device: 'cpu'
2026-02-12 12:36:26,960 - docling.pipeline.base_pipeline - INFO - Processing document Bose-Products 3.pdf
2026-02-12 12:42:01,875 - docling.document_converter - INFO - Finished converting document Bose-Products 3.pdf in 348.62 sec.
2026-02-12 12:42:01,884 - src.etl.extractor - INFO - PDF has 18 pages
2026-02-12 12:42:01,885 - src.etl.extractor - INFO - Found 15 tables in document
2026-02-12 12:42:01,888 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,908 - src.etl.extractor - INFO - Table 0: page 2, 8 columns, 15 rows
2026-02-12 12:42:01,908 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,913 - src.etl.extractor - INFO - Table 1: page 3, 9 columns, 16 rows
2026-02-12 12:42:01,914 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,922 - src.etl.extractor - INFO - Table 2: page 4, 5 columns, 15 rows
2026-02-12 12:42:01,922 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,928 - src.etl.extractor - INFO - Table 3: page 5, 6 columns, 14 rows
2026-02-12 12:42:01,928 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,937 - src.etl.extractor - INFO - Table 4: page 6, 8 columns, 15 rows
2026-02-12 12:42:01,938 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,941 - src.etl.extractor - INFO - Table 5: page 7, 6 columns, 12 rows
2026-02-12 12:42:01,942 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,946 - src.etl.extractor - INFO - Table 6: page 8, 6 columns, 11 rows
2026-02-12 12:42:01,947 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,953 - src.etl.extractor - INFO - Table 7: page 10, 5 columns, 12 rows
2026-02-12 12:42:01,953 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,961 - src.etl.extractor - INFO - Table 8: page 11, 8 columns, 13 rows
2026-02-12 12:42:01,962 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,969 - src.etl.extractor - INFO - Table 9: page 12, 9 columns, 8 rows
2026-02-12 12:42:01,969 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,979 - src.etl.extractor - INFO - Table 10: page 13, 9 columns, 12 rows
2026-02-12 12:42:01,980 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,987 - src.etl.extractor - INFO - Table 11: page 14, 6 columns, 13 rows
2026-02-12 12:42:01,987 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:01,993 - src.etl.extractor - INFO - Table 12: page 15, 6 columns, 13 rows
2026-02-12 12:42:01,993 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:02,004 - src.etl.extractor - INFO - Table 13: page 16, 5 columns, 23 rows
2026-02-12 12:42:02,005 - docling_core.types.doc.document - WARNING - Usage of TableItem.export_to_dataframe() without `doc` argument is deprecated.
2026-02-12 12:42:02,009 - src.etl.extractor - INFO - Table 14: page 17, 3 columns, 21 rows
2026-02-12 12:42:02,043 - src.etl.extractor - INFO - Extracted 15 tables from Bose-Products 3.pdf
2026-02-12 12:42:02,112 - src.etl.extractor - INFO - Saved raw tables to: D:\production local RAG\data\processed\raw_tables.json
2026-02-12 12:42:02,118 - __main__ - INFO - Extraction complete: 1 PDFs, 15 tables in 442.01s
2026-02-12 12:42:02,119 - __main__ - INFO - Stage 2: Normalization      
2026-02-12 12:42:02,120 - src.etl.normalizer - INFO - Normalizing 1 extraction results
2026-02-12 12:42:02,147 - src.etl.normalizer - INFO - Saved normalized products to: D:\production local RAG\data\processed\normalized_products.json
2026-02-12 12:42:02,148 - src.etl.normalizer - INFO - Normalization complete: 86 products from 15 tables (2 exploded)
2026-02-12 12:42:02,148 - __main__ - INFO - Normalization complete: 86 products (2 exploded) in 0.03s
2026-02-12 12:42:02,156 - __main__ - INFO - Stage 4: Loading
2026-02-12 12:42:02,160 - src.etl.loader - INFO - Loading 86 products into database
2026-02-12 12:42:02,163 - src.etl.loader - INFO - Loaded 0 cached embeddings
2026-02-12 12:42:11,891 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:12,530 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:13,451 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:14,326 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:14,933 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:15,412 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:15,920 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:16,443 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:16,935 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:17,420 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:18,466 - src.etl.loader - INFO - Loaded batch 1: 0 inserted, 10 updated
2026-02-12 12:42:19,755 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:20,237 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:20,718 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:21,209 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:21,692 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:22,201 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:22,793 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:23,496 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:24,171 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:24,959 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:25,535 - src.etl.loader - INFO - Loaded batch 2: 0 inserted, 10 updated
2026-02-12 12:42:26,811 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:27,387 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:28,493 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:29,035 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:30,225 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:30,973 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:31,609 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:32,359 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:33,112 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:33,785 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:34,361 - src.etl.loader - INFO - Loaded batch 3: 0 inserted, 10 updated
2026-02-12 12:42:35,691 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:36,402 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:37,059 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:37,660 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:38,409 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:38,989 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:39,759 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:40,304 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:40,874 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:41,433 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:41,994 - src.etl.loader - INFO - Loaded batch 4: 0 inserted, 10 updated
2026-02-12 12:42:43,304 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:44,098 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:44,405 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:44,703 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:45,444 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:46,182 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:46,805 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:47,370 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:47,860 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:48,191 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:48,764 - src.etl.loader - INFO - Loaded batch 5: 0 inserted, 10 updated
2026-02-12 12:42:49,827 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:50,122 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:50,386 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:50,587 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:50,782 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:50,968 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:51,194 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:51,411 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:51,668 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:51,867 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:52,433 - src.etl.loader - INFO - Loaded batch 6: 0 inserted, 10 updated
2026-02-12 12:42:53,313 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:53,519 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:53,792 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:53,983 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:54,167 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:54,367 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:54,559 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:54,798 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:54,993 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:55,168 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:55,714 - src.etl.loader - INFO - Loaded batch 7: 0 inserted, 10 updated
2026-02-12 12:42:56,486 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:56,695 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:56,896 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:57,076 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:57,293 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:57,494 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:57,685 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:57,881 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:58,112 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:58,395 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:42:58,936 - src.etl.loader - INFO - Loaded batch 8: 0 inserted, 10 updated
2026-02-12 12:42:59,743 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:43:00,173 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:43:01,073 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:43:01,783 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:43:02,573 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:43:03,561 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:43:03,901 - src.etl.loader - INFO - Loaded batch 9: 0 inserted, 6 updated
2026-02-12 12:43:04,119 - src.etl.loader - INFO - Load complete: 0 inserted, 86 updated, 0 failed
2026-02-12 12:43:04,338 - __main__ - INFO - Loading complete: 0 inserted, 86 updated, 86 embeddings generated in 62.18s
2026-02-12 12:43:04,340 - __main__ - INFO - Creating vector index...
2026-02-12 12:43:04,344 - src.etl.loader - INFO - Creating vector index...
2026-02-12 12:43:04,656 - src.etl.loader - INFO - Created IVFFlat index with 10 lists for 86 products
2026-02-12 12:43:04,660 - __main__ - INFO - ETL pipeline completed in 505.25s

==================================================
ETL Pipeline Summary
==================================================
Status: completed
Duration: 505.25s
Products created: 86
Products loaded: 86
==================================================
PS D:\production local RAG> python tests\run_accuracy.py                
2026-02-12 12:45:11,707 - __main__ - INFO - Running 20 test cases...    
2026-02-12 12:45:11,707 - src.rag.engine - INFO - Processing query: What's the power of AM10/60?
2026-02-12 12:45:11,712 - src.database - INFO - Initializing database pool: localhost:5433/bose_products
2026-02-12 12:45:11,908 - src.database - INFO - Database pool initialized with 2-10 connections
2026-02-12 12:45:11,941 - __main__ - INFO - [1/20] ✓ direct_01: 0.33 (233ms)
2026-02-12 12:45:11,941 - src.rag.engine - INFO - Processing query: Show me the specs for DM3SE
2026-02-12 12:45:42,269 - __main__ - ERROR - Judge error: 
2026-02-12 12:45:42,290 - __main__ - INFO - [2/20] ✓ direct_02: 0.67 (15ms)
2026-02-12 12:45:42,297 - src.rag.engine - INFO - Processing query: What's the frequency response of IZA 250-LZ?
2026-02-12 12:46:12,612 - __main__ - ERROR - Judge error: 
2026-02-12 12:46:12,612 - __main__ - INFO - [3/20] ✓ direct_03: 0.67 (35ms)
2026-02-12 12:46:12,613 - src.rag.engine - INFO - Processing query: FS2SE specifications
2026-02-12 12:46:29,328 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/generate "HTTP/1.1 200 OK"
2026-02-12 12:46:59,643 - __main__ - ERROR - Judge error: 
2026-02-12 12:46:59,645 - __main__ - INFO - [4/20] ✓ direct_04: 0.67 (16750ms)
2026-02-12 12:46:59,646 - src.rag.engine - INFO - Processing query: Find 70V ceiling speakers for conference rooms
2026-02-12 12:46:59,667 - src.rag.embeddings - INFO - Loaded 0 cached query embeddings
2026-02-12 12:46:59,669 - src.rag.embeddings - INFO - Embedding cache MISS - Generating: 'Find 70V ceiling speakers for ...'
2026-02-12 12:47:07,911 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:47:54,187 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/generate "HTTP/1.1 200 OK"
2026-02-12 12:47:54,200 - __main__ - INFO - [5/20] ✓ semantic_01: 0.72 (54553ms)
2026-02-12 12:47:54,201 - src.rag.engine - INFO - Processing query: What outdoor speakers do you have?
2026-02-12 12:48:09,212 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/generate "HTTP/1.1 200 OK"
2026-02-12 12:48:09,218 - src.rag.embeddings - INFO - Embedding cache MISS - Generating: 'What outdoor speakers do you h...'
2026-02-12 12:48:17,073 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:49:17,644 - src.rag.generator - ERROR - Answer generation error:
2026-02-12 12:49:48,052 - __main__ - ERROR - Judge error: 
2026-02-12 12:49:48,055 - __main__ - INFO - [6/20] ✓ semantic_02: 0.70 (83490ms)
2026-02-12 12:49:48,058 - src.rag.engine - INFO - Processing query: Recommend amplifiers over 250 watts
2026-02-12 12:49:48,064 - src.rag.embeddings - INFO - Embedding cache MISS - Generating: 'Recommend amplifiers over 250 ...'
2026-02-12 12:49:56,514 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:50:48,358 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/generate "HTTP/1.1 200 OK"
2026-02-12 12:51:18,657 - __main__ - ERROR - Judge error: 
2026-02-12 12:51:18,659 - __main__ - INFO - [7/20] ✓ semantic_03: 0.75 (60318ms)
2026-02-12 12:51:18,660 - src.rag.engine - INFO - Processing query: DesignMax speakers for retail
2026-02-12 12:51:32,356 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/generate "HTTP/1.1 200 OK"
2026-02-12 12:51:32,360 - src.rag.embeddings - INFO - Embedding cache MISS - Generating: 'DesignMax speakers for retail...'
2026-02-12 12:51:39,941 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:52:20,435 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/generate "HTTP/1.1 200 OK"
2026-02-12 12:52:20,456 - __main__ - INFO - [8/20] ✓ semantic_04: 0.86 (61793ms)
2026-02-12 12:52:20,457 - src.rag.engine - INFO - Processing query: Arena speakers for live events
2026-02-12 12:52:37,131 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/generate "HTTP/1.1 200 OK"
2026-02-12 12:52:37,135 - src.rag.embeddings - INFO - Embedding cache MISS - Generating: 'Arena speakers for live events...'
2026-02-12 12:52:44,975 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:53:45,521 - src.rag.generator - ERROR - Answer generation error:
2026-02-12 12:54:15,888 - __main__ - ERROR - Judge error: 
2026-02-12 12:54:15,891 - __main__ - INFO - [9/20] ✓ semantic_05: 0.70 (85096ms)
2026-02-12 12:54:15,894 - src.rag.engine - INFO - Processing query: Can I connect 4 speakers at 30W each to a 150W transformer?
2026-02-12 12:54:15,931 - __main__ - INFO - [10/20] ✓ calc_01: 1.00 (34ms)
2026-02-12 12:54:15,931 - src.rag.engine - INFO - Processing query: Can I connect 6 x 30W speakers to 150W transformer?
2026-02-12 12:54:15,932 - __main__ - INFO - [11/20] ✗ calc_02: 0.50 (1ms)
2026-02-12 12:54:15,933 - src.rag.engine - INFO - Processing query: Calculate impedance of 3 x 8 ohm speakers in parallel
2026-02-12 12:54:15,935 - __main__ - INFO - [12/20] ✗ calc_03: 0.00 (2ms)
2026-02-12 12:54:15,936 - src.rag.engine - INFO - Processing query: What's the total impedance of 4 ohm and 8 ohm speakers in series?
2026-02-12 12:54:15,936 - __main__ - INFO - [13/20] ✓ calc_04: 1.00 (1ms)
2026-02-12 12:54:15,936 - src.rag.engine - INFO - Processing query: What transformer do I need for 200W of speakers?
2026-02-12 12:54:15,938 - __main__ - INFO - [14/20] ✗ calc_05: 0.00 (1ms)
2026-02-12 12:54:15,939 - src.rag.engine - INFO - Processing query: AM10/60/80 power handling
2026-02-12 12:54:16,366 - __main__ - INFO - [15/20] ✓ edge_01: 1.00 (426ms)
2026-02-12 12:54:16,366 - src.rag.engine - INFO - Processing query: What's the wattage of a nonexistent model XYZ123?
2026-02-12 12:54:16,386 - src.rag.embeddings - INFO - Embedding cache MISS - Generating: 'What's the wattage of a nonexi...'
2026-02-12 12:54:27,563 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:55:16,670 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/generate "HTTP/1.1 200 OK"
2026-02-12 12:55:16,698 - __main__ - INFO - [16/20] ✗ edge_02: 0.00 (60327ms)
2026-02-12 12:55:16,699 - __main__ - INFO - [17/20] ✓ edge_03: 1.00 (0ms)
2026-02-12 12:55:16,700 - src.rag.engine - INFO - Processing query: Compare power handling of AM10/60 vs AM20/60
2026-02-12 12:55:16,827 - __main__ - INFO - [18/20] ✓ complex_01: 0.50 (126ms)
2026-02-12 12:55:16,828 - src.rag.engine - INFO - Processing query: What 70V speakers work with a 300W PowerSpace amplifier?
2026-02-12 12:55:16,831 - src.rag.embeddings - INFO - Embedding cache MISS - Generating: 'What 70V speakers work with a ...'
2026-02-12 12:55:23,977 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/embeddings "HTTP/1.1 200 OK"
2026-02-12 12:55:24,073 - __main__ - INFO - [19/20] ✓ complex_02: 1.00 (7246ms)
2026-02-12 12:55:24,075 - src.rag.engine - INFO - Processing query: What's the sensitivity of EM90?
2026-02-12 12:55:54,389 - __main__ - ERROR - Judge error: 
2026-02-12 12:55:54,400 - __main__ - INFO - [20/20] ✗ citation_01: 0.00 (22ms)

============================================================
ACCURACY EVALUATION REPORT
============================================================
Timestamp: 2026-02-12T12:55:54.513750
Total Tests: 20
Passed: 15
Failed: 5
Accuracy: 75.0%
Accuracy: 75.0%
Hallucination Rate: 0.0%
Faithfulness: 100.0%
Avg Duration: 21523ms

By Category:
  direct_lookup: 4/4 (100.0%)
  semantic_search: 5/5 (100.0%)
  calculation: 2/5 (40.0%)
  edge_case: 2/3 (66.7%)
  complex: 2/2 (100.0%)
  citation: 0/1 (0.0%)

Failed Tests:
  - calc_02: Can I connect 6 x 30W speakers to 150W transformer...      
  - calc_03: Calculate impedance of 3 x 8 ohm speakers in paral...      
  - calc_05: What transformer do I need for 200W of speakers?...        
  - edge_02: What's the wattage of a nonexistent model XYZ123?...       
  - citation_01: What's the sensitivity of EM90?...
============================================================
