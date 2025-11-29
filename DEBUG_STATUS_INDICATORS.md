# Debug Guide: Status Indicators Not Turning Green

## Current Situation

- ✅ API `/health` endpoint returns: `{"falkordb":true,"graphiti":true,"overall":true}`
- ✅ Server logs show: "✅ All systems operational"
- ❌ UI status indicators remain red

## Debugging Steps

### Step 1: Check Browser Console

Open the browser console:
- **Mac**: `Cmd + Option + I` or `F12`
- **Windows**: `Ctrl + Shift + I` or `F12`

Go to the **Console** tab and look for these messages:

```javascript
Health check response: {falkordb: true, graphiti: true, overall: true}
FalkorDB element: <span class="status-dot..." ...>  Status: true
Graphiti element: <span class="status-dot..." ...>  Status: true
```

### Step 2: Check for JavaScript Errors

In the Console tab, look for any **red error messages**. Common issues:

1. **Elements not found** - If you see:
   ```
   Cannot read properties of null (reading 'classList')
   ```
   This means the elements don't exist when checkHealth() runs.

2. **CORS errors** - If you see:
   ```
   Access to fetch at 'http://localhost:8080/health' has been blocked by CORS
   ```
   This means the API request is being blocked.

3. **Network errors** - If you see:
   ```
   Failed to fetch
   ```
   This means the API is not reachable.

### Step 3: Check Network Tab

1. Open DevTools Network tab
2. Refresh the page (`Cmd+R`)
3. Look for a request to `/health`
4. Click on it and check:
   - **Status**: Should be `200 OK`
   - **Response**: Should show `{"falkordb":true,"graphiti":true,"overall":true}`

### Step 4: Inspect Elements

1. Right-click on the red dot next to "FalkorDB (ORM)"
2. Select "Inspect Element"
3. Check the HTML - should look like:
   ```html
   <span class="status-dot offline" id="falkordbDot"></span>
   ```

4. After the health check runs, it should change to:
   ```html
   <span class="status-dot online" id="falkordbDot"></span>
   ```

### Step 5: Manual Test in Console

Open the Console tab and run this:

```javascript
// Test if elements exist
console.log('falkordbDot:', document.getElementById('falkordbDot'));
console.log('graphitiDot:', document.getElementById('graphitiDot'));

// Test fetch directly
fetch('http://localhost:8080/health')
  .then(r => r.json())
  .then(d => console.log('Health response:', d))
  .catch(e => console.error('Health error:', e));

// Test class manipulation
const dot = document.getElementById('falkordbDot');
if (dot) {
  dot.classList.remove('offline');
  dot.classList.add('online');
  console.log('Manually set to online, classes:', dot.className);
}
```

If the last command makes the dot turn green, then the CSS is working and it's a JavaScript execution issue.

## Common Issues and Fixes

### Issue 1: JavaScript File Not Loading

**Check**: Network tab should show `/static/js/app.js` with status `200 OK`

**Fix**: Hard refresh with `Cmd + Shift + R`

### Issue 2: Elements Not Found (null)

**Symptom**: Console shows elements as `null`

**Fix**: The JavaScript is running before the HTML loads. This shouldn't happen with DOMContentLoaded, but check if `app.js` is loaded in the right place (should be at the end of `</body>` tag).

### Issue 3: CORS Blocking Request

**Symptom**: Console shows CORS error

**Fix**: The API needs to allow the origin. Check `config/config.yaml`:
```yaml
cors_origins:
  - "http://localhost:8080"
```

### Issue 4: CSS Classes Not Working

**Symptom**: Classes change in HTML but color doesn't change

**Fix**: Check if `/static/css/styles.css` loaded successfully:
1. Network tab → look for `styles.css`
2. Should be `200 OK`
3. Check computed styles in Elements tab

### Issue 5: API Returns Wrong Data

**Symptom**: Health response shows `false` values

**Fix**: Check server is running correctly:
```bash
curl http://localhost:8080/health
```

## Test Page

A diagnostic test page has been created at `/tmp/test_check.html`. Open it in your browser - it should show:
- Real-time log of what's happening
- Two dots that turn from red to green
- If this works but the main page doesn't, the issue is in app.js loading/execution

## Quick Manual Fix Test

To test if the problem is just JavaScript not running:

1. Open http://localhost:8080 in browser
2. Open Console (F12)
3. Paste this and press Enter:

```javascript
document.getElementById('falkordbDot').className = 'status-dot online';
document.getElementById('graphitiDot').className = 'status-dot online';
```

If the dots turn green, the CSS works and it's just the JavaScript not executing properly.

## Next Steps Based on Console Output

### If you see: "Health check response: {falkordb: true, ...}"
The API call is working. Check if you see "Setting to online" or if there are errors after that.

### If you see: "API Error: ..." or "Health check failed: ..."
The API call is failing. Check:
1. Is the server running? `curl http://localhost:8080/health`
2. Is CORS configured correctly?
3. Is the API_BASE_URL correct? Check console: `console.log(API_BASE_URL)`

### If you don't see any health check messages at all
The JavaScript isn't running. Check:
1. Is `app.js` loaded? (Network tab)
2. Are there any JavaScript errors before the health check runs?
3. Try opening in an Incognito window

## Expected vs Actual

**Expected Sequence:**
1. Page loads
2. DOMContentLoaded event fires
3. checkHealth() is called
4. Fetch to /health returns `{falkordb: true, graphiti: true}`
5. Elements get `online` class added, `offline` class removed
6. CSS makes dots green

**Find where this breaks by checking the console logs at each step!**

## Report Back

Please check the browser console and report:
1. What do you see when the page loads?
2. Are there any red error messages?
3. Does the `/health` request appear in Network tab?
4. What's the response of `/health`?
5. Do the elements exist? (Check with `document.getElementById('falkordbDot')`)

This will help identify exactly where the issue is occurring.
