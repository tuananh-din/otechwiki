import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.ingest import ingest_pdf, ingest_ppt
from app.models.user import Base
from app.models.document import Document, Chunk
from app.core.config import get_settings

async def test_ingest():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    uploads_dir = 'backend/uploads'
    files = [
        ('Qrevo S Pro Launching Plan 02.26.pptx', 'ppt'),
        ('[FIDT]-TÀI LIỆU TỌA ĐÀM QUẢN LÝ GIA SẢN 2025.pdf', 'pdf')
    ]
    
    async with async_session() as session:
        for filename, file_type in files:
            file_path = os.path.join(uploads_dir, filename)
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                continue
                
            print(f"\n--- Testing Ingestion for: {filename} ---")
            
            # Create a temporary document record
            doc = Document(title=f"Test_{filename}", status="pending", source_path=filename, source_type="file")
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            
            try:
                if file_type == 'pdf':
                    num_chunks = await ingest_pdf(session, doc.id, file_path)
                else:
                    num_chunks = await ingest_ppt(session, doc.id, file_path)
                
                print(f"Success! {num_chunks} chunks created.")
                
                # Check some chunks
                from sqlalchemy import select
                result = await session.execute(select(Chunk).where(Chunk.document_id == doc.id).limit(5))
                chunks = result.scalars().all()
                for i, c in enumerate(chunks):
                    print(f"Chunk {i} (len {len(c.content)}): {c.content[:200]}...")
            except Exception as e:
                print(f"Error ingesting {filename}: {e}")
            finally:
                # Cleanup (optional, but keep for now to see results in DB)
                pass

if __name__ == "__main__":
    asyncio.run(test_ingest())
