import asyncio, sys
sys.path.insert(0, '.')

from core.kimi_cli_adapter import KimiCLIAdapter

async def test():
    adapter = KimiCLIAdapter()
    print(f"Kimi CLI found: {adapter.cli_path}")
    
    result = await adapter.complete(
        "Напиши короткий пост про AI автоматизацию для Telegram, 3 предложения",
        max_tokens=200
    )
    print("\n=== RESULT ===")
    # Write to file to avoid cp1251 console encoding issues
    with open('kimi_cli_result.txt', 'w', encoding='utf-8') as f:
        f.write(result)
    # Print ASCII-safe preview
    print("[Result saved to kimi_cli_result.txt]")
    print("Preview (first 200 chars):")
    print(result[:200].encode('ascii', 'replace').decode('ascii'))

asyncio.run(test())
