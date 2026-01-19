"""
Test OCR Integration for 4 Agents: Support, Legal, Analyst, Marketing
Tests all agent-specific OCR helper functions
"""

import sys
import os
sys.path.insert(0, '/home/genesis/genesis-rebuild')

from infrastructure.ocr.ocr_agent_tool import (
    support_agent_ticket_image_processor,
    legal_agent_contract_parser,
    analyst_agent_chart_data_extractor,
    marketing_agent_visual_analyzer
)

def test_support_agent_ocr():
    """Test Support Agent OCR integration"""
    print("\n" + "="*60)
    print("TEST 1: Support Agent - Process Ticket Image")
    print("="*60)

    result = support_agent_ticket_image_processor(
        "/home/genesis/genesis-rebuild/data/ocr_test_images/test_ticket.png"
    )

    print(f"✓ Valid: {result.get('valid', False)}")
    print(f"✓ Text Length: {len(result.get('text', ''))} chars")
    print(f"✓ Likely Issue Report: {result.get('likely_issue_report', False)}")
    print(f"✓ Detected Issues: {result.get('detected_issues', [])}")
    print(f"✓ High Urgency: {result.get('urgency_high', False)}")
    print(f"✓ Inference Time: {result.get('inference_time', 0):.3f}s")

    assert result['valid'] == True, "Support agent OCR should succeed"
    assert len(result['text']) > 0, "Should extract text"
    print("\n✅ SUPPORT AGENT OCR: PASS")
    return result

def test_legal_agent_ocr():
    """Test Legal Agent OCR integration"""
    print("\n" + "="*60)
    print("TEST 2: Legal Agent - Parse Contract Image")
    print("="*60)

    result = legal_agent_contract_parser(
        "/home/genesis/genesis-rebuild/data/ocr_test_images/test_invoice.png"
    )

    print(f"✓ Valid: {result.get('valid', False)}")
    print(f"✓ Text Length: {len(result.get('text', ''))} chars")
    print(f"✓ Likely Legal Doc: {result.get('likely_legal_doc', False)}")
    print(f"✓ Legal Terms Found: {result.get('found_legal_terms', [])}")
    print(f"✓ Character Count: {result.get('char_count', 0)}")
    print(f"✓ Inference Time: {result.get('inference_time', 0):.3f}s")

    assert result['valid'] == True, "Legal agent OCR should succeed"
    assert len(result['text']) > 0, "Should extract text"
    print("\n✅ LEGAL AGENT OCR: PASS")
    return result

def test_analyst_agent_ocr():
    """Test Analyst Agent OCR integration"""
    print("\n" + "="*60)
    print("TEST 3: Analyst Agent - Extract Chart Data")
    print("="*60)

    result = analyst_agent_chart_data_extractor(
        "/home/genesis/genesis-rebuild/data/ocr_test_images/test_invoice.png"
    )

    print(f"✓ Valid: {result.get('valid', False)}")
    print(f"✓ Text Length: {len(result.get('text', ''))} chars")
    print(f"✓ Likely Chart/Graph: {result.get('likely_chart_or_graph', False)}")
    print(f"✓ Numbers Detected: {result.get('numbers_detected', [])}")
    print(f"✓ Numeric Data Count: {result.get('numeric_data_count', 0)}")
    print(f"✓ Inference Time: {result.get('inference_time', 0):.3f}s")

    assert result['valid'] == True, "Analyst agent OCR should succeed"
    assert len(result['text']) > 0, "Should extract text"
    print("\n✅ ANALYST AGENT OCR: PASS")
    return result

def test_marketing_agent_ocr():
    """Test Marketing Agent OCR integration"""
    print("\n" + "="*60)
    print("TEST 4: Marketing Agent - Analyze Competitor Visual")
    print("="*60)

    result = marketing_agent_visual_analyzer(
        "/home/genesis/genesis-rebuild/data/ocr_test_images/test_ticket.png"
    )

    print(f"✓ Valid: {result.get('valid', False)}")
    print(f"✓ Text Length: {len(result.get('text', ''))} chars")
    print(f"✓ Likely Marketing Material: {result.get('likely_marketing_material', False)}")
    print(f"✓ CTA Keywords Found: {result.get('cta_keywords', [])}")
    print(f"✓ Marketing Terms: {result.get('marketing_terms_found', [])}")
    print(f"✓ Inference Time: {result.get('inference_time', 0):.3f}s")

    assert result['valid'] == True, "Marketing agent OCR should succeed"
    assert len(result['text']) > 0, "Should extract text"
    print("\n✅ MARKETING AGENT OCR: PASS")
    return result

def test_error_handling():
    """Test error handling for invalid inputs"""
    print("\n" + "="*60)
    print("TEST 5: Error Handling - Invalid File")
    print("="*60)

    result = support_agent_ticket_image_processor("/nonexistent/file.png")

    print(f"✓ Valid: {result.get('valid', False)}")
    print(f"✓ Error Present: {'error' in result}")
    print(f"✓ Error Message: {result.get('error', 'N/A')}")

    assert result['valid'] == False, "Should fail on nonexistent file"
    assert 'error' in result, "Should contain error message"
    print("\n✅ ERROR HANDLING: PASS")
    return result

def test_performance():
    """Test OCR performance with caching"""
    print("\n" + "="*60)
    print("TEST 6: Performance - Cache Hit Test")
    print("="*60)

    import time

    # First call (cache miss)
    start1 = time.time()
    result1 = support_agent_ticket_image_processor(
        "/home/genesis/genesis-rebuild/data/ocr_test_images/test_ticket.png"
    )
    time1 = time.time() - start1

    # Second call (cache hit)
    start2 = time.time()
    result2 = support_agent_ticket_image_processor(
        "/home/genesis/genesis-rebuild/data/ocr_test_images/test_ticket.png"
    )
    time2 = time.time() - start2

    print(f"✓ First call (cache miss): {time1:.3f}s")
    print(f"✓ Second call (cache hit): {time2:.3f}s")
    print(f"✓ Speedup: {time1/time2:.1f}x faster")
    print(f"✓ Results identical: {result1 == result2}")

    assert time2 < time1, "Second call should be faster (cached)"
    assert result1 == result2, "Results should be identical"
    print("\n✅ PERFORMANCE TEST: PASS")
    return {'first_call': time1, 'second_call': time2, 'speedup': time1/time2}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("OCR AGENT INTEGRATION TEST SUITE")
    print("Testing: Support, Legal, Analyst, Marketing Agents")
    print("="*60)

    try:
        # Run all tests
        results = {}
        results['support'] = test_support_agent_ocr()
        results['legal'] = test_legal_agent_ocr()
        results['analyst'] = test_analyst_agent_ocr()
        results['marketing'] = test_marketing_agent_ocr()
        results['error_handling'] = test_error_handling()
        results['performance'] = test_performance()

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print("✅ Support Agent OCR:    PASS")
        print("✅ Legal Agent OCR:      PASS")
        print("✅ Analyst Agent OCR:    PASS")
        print("✅ Marketing Agent OCR:  PASS")
        print("✅ Error Handling:       PASS")
        print("✅ Performance (Caching): PASS")
        print("\n🎉 ALL 6 TESTS PASSED!")
        print("="*60)

        # Performance metrics
        print("\nPERFORMANCE METRICS:")
        print(f"  Average Inference: {sum(r.get('inference_time', 0) for r in [results['support'], results['legal'], results['analyst'], results['marketing']]) / 4:.3f}s")
        print(f"  Cache Speedup: {results['performance']['speedup']:.1f}x")
        print(f"  Total Tests: 6/6 PASSED (100%)")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
