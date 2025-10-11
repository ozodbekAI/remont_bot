"""
Skript bazani qayta yaratish uchun.
OGOHLANTIRISH: Bu barcha ma'lumotlarni o'chiradi!

Foydalanish: python scripts/recreate_db.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.engine import DatabaseManager


async def main():
    print("⚠️  OGOHLANTIRISH: Bu barcha ma'lumotlarni o'chiradi!")
    print("⚠️  Agar davom etsangiz, barcha jadvallar qayta yaratiladi.")
    confirm = input("\nDavom etmoqchimisiz? (YES ni to'liq yozing): ")
    
    if confirm != "YES":
        print("❌ Bekor qilindi")
        return
    
    try:
        print("\n🗑️  Eski jadvallarni o'chirish...")
        await DatabaseManager.drop_tables()
        print("✅ Eski jadvallar o'chirildi")
        
        print("\n🔨 Yangi jadvallarni yaratish...")
        await DatabaseManager.create_tables()
        print("✅ Yangi jadvallar yaratildi")
        
        print("\n✨ Tayyor! Endi ma'lumotlarni yuklash uchun:")
        print("   python scripts/init_data.py")
        
    except Exception as e:
        print(f"\n❌ Xatolik: {e}")
        print("\nQo'lda bajarib ko'ring:")
        print("  psql -U postgres")
        print("  DROP DATABASE IF EXISTS service_bot;")
        print("  CREATE DATABASE service_bot;")
        print("  \\q")
    finally:
        await DatabaseManager.close()


if __name__ == "__main__":
    asyncio.run(main())