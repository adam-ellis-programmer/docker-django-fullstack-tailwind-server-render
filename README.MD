# Django Social Feed - Advertisement Mixing System

## Overview

The ad mixing system integrates advertisements into the social media feed by inserting ads between posts at configurable intervals. The system supports user-targeted advertising based on interests and tracks impressions for analytics.

## Function Call Flow

```
User Request → Django View → Ad Mixing → Template Rendering
```

### 1. Initial Page Load
```
public_posts() 
├── get_user_from_jwt() → Returns user object
├── Paginator() → Creates paginated posts
└── mix_posts_with_ads() → Mixes posts with ads
    ├── UserInterest.objects.filter() → Gets user interests
    └── get_targeted_ad() → Selects appropriate ad
        ├── Advertisement.objects.filter() → Gets active ads
        └── ad.is_campaign_active → Checks if campaign is running
```

### 2. Infinite Scroll (AJAX)
```
load_more_posts()
├── get_user_from_jwt() → Returns user object  
├── Paginator() → Gets next page of posts
└── mix_posts_with_ads() → Mixes posts with ads
    └── get_targeted_ad() → Selects appropriate ad
```

## Core Functions

### `mix_posts_with_ads(posts, user, ads_frequency)`

**Purpose**: Main function that combines posts and advertisements

**Parameters**:
- `posts`: QuerySet of Post objects from pagination
- `user`: Current user object (for targeting)
- `ads_frequency`: Integer (insert ad every N posts)

**Process**:
1. Convert posts QuerySet to Python list
2. Initialize empty `mixed_items` list for output
3. Query user interests from database
4. Loop through each post:
   - Add post to `mixed_items`
   - Check if position matches ad frequency: `(i + 1) % ads_frequency == 0`
   - If yes, call `get_targeted_ad()` and append result
5. Return `mixed_items` list with posts and ads

### `get_targeted_ad(user, user_interests)`

**Purpose**: Selects the most appropriate advertisement for the user

**Parameters**:
- `user`: User object (optional)
- `user_interests`: QuerySet of UserInterest objects

**Process**:
1. Query all active advertisements: `Advertisement.objects.filter(is_active=True)`
2. Filter by campaign status using `ad.is_campaign_active` property
3. If user has interests:
   - Match ad `target_audience` with user interest names
   - Weight ads by number of matching interests
   - Return random weighted selection
4. Fallback: Return random active ad
5. Update impression counter: `ad.impressions += 1`

## Ad Insertion Logic

### Frequency Calculation
```python
should_add_ad = (i + 1) % ads_frequency == 0
```

- `i`: Zero-based loop index (0, 1, 2, 3...)
- `i + 1`: Converts to position number (1, 2, 3, 4...)
- `% ads_frequency`: Modulo operation finds remainder
- `== 0`: True when position is divisible by frequency

### Examples

**ads_frequency = 10:**
- Position 10: `10 % 10 = 0` → Insert ad
- Position 20: `20 % 10 = 0` → Insert ad  
- Position 15: `15 % 10 = 5` → No ad

**ads_frequency = 5:**
- Position 5: `5 % 5 = 0` → Insert ad
- Position 10: `10 % 5 = 0` → Insert ad

## User Interest Targeting

### Database Query
```python
user_interests = UserInterest.objects.filter(user=user, score__gte=1.0)[:10]
```

### Matching Process
1. Extract interest names: `[interest.interest for interest in user_interests]`
2. Check each ad's `target_audience` JSON field
3. Find intersection: `set(ad.target_audience) & set(interest_names)`
4. Weight ads by number of matches: `[ad] * len(matches)`
5. Random selection from weighted list

### Example Matching
```
User interests: ["hiking", "photography", "travel"]
Ad target_audience: ["hiking", "outdoor", "adventure"] 
Match: {"hiking"} → Weight = 1
```

## Template Integration

### Template Context
```python
context = {
    'items': mixed_items,  # List of posts and ads
    'jwt_user': jwt_user,
    'has_next': first_page.has_next(),
}
```

### Template Logic
```html
{% for item in items %}
  {% if item.type == 'advertisement' %}
    {% include 'components/advertisement.html' with ad=item %}
  {% else %}
    <!-- Regular post HTML -->
  {% endif %}
{% endfor %}
```

## Analytics Tracking

### Impression Tracking
- Automatic: `ad.impressions += 1` when ad is displayed
- Database update: `ad.save(update_fields=['impressions'])`

### Click Tracking  
- JavaScript: `trackAdClick(adId)` function
- AJAX endpoint: `track_ad_click()` view
- Database update: `ad.clicks += 1`

## Configuration

### View Settings
```python
# Public posts: 10 posts per page, ad every 10 posts
paginator = Paginator(posts, 10)
mixed_items = mix_posts_with_ads(first_page, jwt_user, ads_frequency=10)

# User posts: Less frequent ads
mixed_items = mix_posts_with_ads(first_page, jwt_user, ads_frequency=15)
```

### Database Requirements
- `Advertisement.is_active = True`
- `Advertisement.is_campaign_active` property returns `True`
- User must have `UserInterest` records for targeting

## Debugging

### Logging Output
```
=== MIX_POSTS_WITH_ADS DEBUG ===
Input: 10 posts, ads_frequency: 10
User: sarahadventure@example.com
Found 5 user interests
Position 10: should_add_ad = True
Selected targeted ad: ad_001
Total items: 11, Ads inserted: 1
```

### Common Issues
- No ads showing: Check `is_campaign_active` property logic
- Wrong frequency: Verify `ads_frequency` parameter
- No targeting: Ensure `UserInterest` records exist