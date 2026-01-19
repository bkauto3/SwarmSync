# ⭐ Improved Agent Rating Formula

**Scientific approach to calculating agent ratings with confidence intervals**

---

## 🎯 Goals

1. **Accurate**: Reflect true agent quality
2. **Fair**: Don't penalize new agents too harshly
3. **Transparent**: Users understand how ratings work
4. **Dynamic**: Recent performance matters more
5. **Confident**: Show confidence level based on sample size

---

## 📊 Current Formula (Needs Improvement)

```typescript
const calculateRating = (trustScore: number, successCount: number, failureCount: number) => {
  const totalRuns = successCount + failureCount;
  if (totalRuns === 0) {
    return Math.max(3.5, Math.min(5, +(trustScore / 20).toFixed(1)));
  }
  const successRate = successCount / totalRuns;
  const combinedScore = (successRate * 0.7 + (trustScore / 100) * 0.3) * 5;
  return Math.max(3.0, Math.min(5.0, +combinedScore.toFixed(1)));
};
```

**Problems:**

- ❌ Doesn't account for recency (old failures hurt forever)
- ❌ No confidence interval (1 success = 5 stars?)
- ❌ Arbitrary weights (why 70/30?)
- ❌ No minimum threshold (unreliable with <10 runs)
- ❌ Doesn't consider execution time or cost

---

## ✅ Improved Formula

### **Multi-Factor Rating System**

```typescript
interface RatingFactors {
  successRate: number; // 0-1
  trustScore: number; // 0-100
  totalRuns: number; // Count
  recentSuccessRate: number; // 0-1 (last 30 days)
  avgExecutionTime: number; // Seconds
  avgCost: number; // Cents
  reviewScore: number; // 0-5 (user reviews)
  reviewCount: number; // Count
}

interface RatingResult {
  rating: number; // 0-5
  confidence: number; // 0-1
  label: string; // "Excellent", "Good", etc.
  showRating: boolean; // Hide if insufficient data
}

function calculateImprovedRating(factors: RatingFactors): RatingResult {
  const { successRate, trustScore, totalRuns, recentSuccessRate, reviewScore, reviewCount } =
    factors;

  // Minimum threshold: Need at least 10 runs OR 3 reviews to show rating
  const hasEnoughData = totalRuns >= 10 || reviewCount >= 3;

  if (!hasEnoughData) {
    return {
      rating: 0,
      confidence: 0,
      label: 'New Agent',
      showRating: false,
    };
  }

  // 1. Success Rate Component (35%)
  //    Recent performance weighted 2x more than historical
  const weightedSuccessRate = successRate * 0.4 + recentSuccessRate * 0.6;
  const successComponent = weightedSuccessRate * 0.35;

  // 2. Trust Score Component (20%)
  //    Platform-assigned trust based on security, compliance, etc.
  const trustComponent = (trustScore / 100) * 0.2;

  // 3. Volume/Confidence Component (15%)
  //    More runs = more confidence in rating
  //    Logarithmic scale: 10 runs = 0.5, 100 runs = 0.8, 1000 runs = 1.0
  const volumeFactor = Math.min(Math.log10(totalRuns) / 3, 1.0);
  const volumeComponent = volumeFactor * 0.15;

  // 4. User Review Component (30%)
  //    Direct user feedback is most valuable
  //    Only if reviews exist
  let reviewComponent = 0;
  if (reviewCount > 0) {
    // Normalize review score (0-5) to 0-1
    const normalizedReviewScore = reviewScore / 5;
    // Weight by review count (more reviews = more weight)
    const reviewWeight = Math.min(reviewCount / 20, 1.0); // Max weight at 20 reviews
    reviewComponent = normalizedReviewScore * reviewWeight * 0.3;
  } else {
    // If no reviews, redistribute weight to success rate
    const redistributedSuccessComponent = weightedSuccessRate * 0.3;
    reviewComponent = redistributedSuccessComponent;
  }

  // Combine all components
  const combinedScore = successComponent + trustComponent + volumeComponent + reviewComponent;

  // Scale to 0-5 rating
  const rating = combinedScore * 5;

  // Calculate confidence level
  const confidence = calculateConfidence(totalRuns, reviewCount);

  // Determine label
  const label = getRatingLabel(rating);

  return {
    rating: Math.max(0, Math.min(5, +rating.toFixed(1))),
    confidence,
    label,
    showRating: true,
  };
}

function calculateConfidence(totalRuns: number, reviewCount: number): number {
  // Confidence based on sample size
  // Uses Wilson score interval approach
  const runConfidence = Math.min(totalRuns / 100, 1.0);
  const reviewConfidence = Math.min(reviewCount / 20, 1.0);

  // Weighted average (runs 60%, reviews 40%)
  return runConfidence * 0.6 + reviewConfidence * 0.4;
}

function getRatingLabel(rating: number): string {
  if (rating >= 4.5) return 'Excellent';
  if (rating >= 4.0) return 'Very Good';
  if (rating >= 3.5) return 'Good';
  if (rating >= 3.0) return 'Fair';
  if (rating >= 2.0) return 'Poor';
  return 'Very Poor';
}
```

---

## 📈 Rating Display Examples

### **Example 1: New Agent (10 runs, no reviews)**

```typescript
{
  successRate: 0.9,           // 9/10 successful
  trustScore: 75,             // Platform trust
  totalRuns: 10,
  recentSuccessRate: 0.9,
  reviewScore: 0,
  reviewCount: 0,
}

// Result:
{
  rating: 4.1,
  confidence: 0.06,           // Low confidence (only 10 runs)
  label: 'Very Good',
  showRating: true,
}

// Display: ⭐ 4.1 (10 runs) ⚠️ Low confidence
```

### **Example 2: Established Agent (150 runs, 12 reviews)**

```typescript
{
  successRate: 0.95,          // 143/150 successful
  trustScore: 85,
  totalRuns: 150,
  recentSuccessRate: 0.97,    // Recent performance even better
  reviewScore: 4.6,           // Average user review
  reviewCount: 12,
}

// Result:
{
  rating: 4.7,
  confidence: 0.90,           // High confidence
  label: 'Excellent',
  showRating: true,
}

// Display: ⭐ 4.7 (150 runs, 12 reviews) ✅ High confidence
```

### **Example 3: Declining Performance**

```typescript
{
  successRate: 0.85,          // Historical: 85/100
  trustScore: 70,
  totalRuns: 100,
  recentSuccessRate: 0.60,    // Recent: only 60% (declining!)
  reviewScore: 3.8,
  reviewCount: 8,
}

// Result:
{
  rating: 3.4,                // Pulled down by recent performance
  confidence: 0.60,
  label: 'Fair',
  showRating: true,
}

// Display: ⭐ 3.4 (100 runs, 8 reviews) ⚠️ Recent performance declining
```

---

## 🎨 UI Display Recommendations

### **Star Display**

```tsx
<div className="flex items-center gap-2">
  {/* Star rating */}
  <div className="flex items-center gap-1">
    <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
    <span className="font-semibold">{rating.toFixed(1)}</span>
  </div>

  {/* Confidence indicator */}
  {confidence < 0.3 && (
    <Badge variant="outline" className="text-xs">
      Low confidence
    </Badge>
  )}

  {/* Run count */}
  <span className="text-xs text-muted-foreground">
    ({totalRuns.toLocaleString()} runs
    {reviewCount > 0 && `, ${reviewCount} reviews`})
  </span>

  {/* Label */}
  <Badge variant="secondary" className="text-xs">
    {label}
  </Badge>
</div>
```

### **Detailed Breakdown (Tooltip)**

```tsx
<Tooltip>
  <TooltipTrigger>
    <Info className="h-3 w-3 text-muted-foreground" />
  </TooltipTrigger>
  <TooltipContent>
    <div className="space-y-1 text-xs">
      <div>Success Rate: {(successRate * 100).toFixed(0)}%</div>
      <div>Recent Success: {(recentSuccessRate * 100).toFixed(0)}%</div>
      <div>Trust Score: {trustScore}/100</div>
      {reviewCount > 0 && <div>User Reviews: {reviewScore.toFixed(1)}/5.0</div>}
      <div className="pt-1 border-t">Confidence: {(confidence * 100).toFixed(0)}%</div>
    </div>
  </TooltipContent>
</Tooltip>
```

---

## 🔄 Implementation Steps

1. **Update Database Schema**
   - [ ] Add `recentSuccessRate` field (calculated from last 30 days)
   - [ ] Add `reviewScore` field (average of user reviews)
   - [ ] Add `reviewCount` field
   - [ ] Add `ratingConfidence` field

2. **Create Rating Service**
   - [ ] Implement `calculateImprovedRating()` function
   - [ ] Create background job to recalculate ratings daily
   - [ ] Add API endpoint to get rating breakdown

3. **Update Frontend Components**
   - [ ] Update `AgentCard` component
   - [ ] Update agent detail page
   - [ ] Add rating tooltip with breakdown
   - [ ] Add confidence indicator

4. **Add User Reviews**
   - [ ] Create review submission form
   - [ ] Add review moderation
   - [ ] Display reviews on agent page
   - [ ] Calculate average review score

5. **Testing**
   - [ ] Test with various scenarios
   - [ ] Verify confidence calculations
   - [ ] Test edge cases (0 runs, 1 run, etc.)
   - [ ] A/B test new formula vs. old

---

## 📊 Rating Distribution Goals

Target distribution across all agents:

- **5.0 - 4.5** (Excellent): 10-15% of agents
- **4.4 - 4.0** (Very Good): 25-30% of agents
- **3.9 - 3.5** (Good): 30-35% of agents
- **3.4 - 3.0** (Fair): 15-20% of agents
- **2.9 - 0.0** (Poor): 5-10% of agents

This creates a **normal distribution** that helps users differentiate quality.

---

**See Also**:

- `AGENT_PRICING_GUIDE.md` - Pricing recommendations
- `COMPLETE_TODO_LIST.md` - Implementation tasks
