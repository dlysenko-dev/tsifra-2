import asyncio, sys
from pathlib import Path
sys.path.insert(0, '.')
try:
    from dotenv import load_dotenv
    load_dotenv(str(Path('.') / '.env'), override=True)
except ImportError:
    pass
from core.llm_router import LLMRouter
async def test():
    llm = LLMRouter()
    result = await llm.complete("Привет, работаешь?", max_tokens=50)
    with open('test_llm_result.txt', 'w', encoding='utf-8') as f:
        f.write(result)
    print("RESULT saved to test_llm_result.txt")
    print("Preview:", result[:100].encode('ascii', 'replace').decode('ascii'))
asyncio.run(test())
