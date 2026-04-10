# 🚀 Deployment Guide - Texas OSOW Permit Converter

## Deploy to Render.com (FREE - Recommended)

### Step 1: Prepare Your Code

You need to push these files to GitHub:

```
permit-converter/
├── api_server.py                 # Flask API
├── parse_permit.py               # Parser logic
├── permit_converter_app.html     # Frontend
├── requirements.txt              # Python dependencies
├── Procfile                      # Tells Render how to start app
└── README.md                     # Documentation
```

**All files are ready in `/home/claude/`** - just need to get them to GitHub.

### Step 2: Create GitHub Repository

#### Option A: Using GitHub Desktop or Git CLI

```bash
# Download all files from /mnt/user-data/outputs/
# Then on your computer:

git init
git add .
git commit -m "Initial commit - Texas OSOW Permit Converter"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/permit-converter.git
git push -u origin main
```

#### Option B: Upload Directly to GitHub

1. Go to https://github.com/new
2. Create repo: `permit-converter`
3. Click "uploading an existing file"
4. Drag all 5 files from `/mnt/user-data/outputs/`
5. Commit

### Step 3: Deploy to Render

1. **Sign up at Render.com**
   - Go to https://render.com
   - Sign up with GitHub (easiest)

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Select `permit-converter`

3. **Configure Service**
   ```
   Name: permit-converter (or your choice)
   Region: Oregon (US West) - closest to Texas
   Branch: main
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn api_server:app
   ```

4. **Select Free Plan**
   - Instance Type: Free
   - Click "Create Web Service"

5. **Wait for Deploy**
   - Takes ~5 minutes
   - Watch the logs
   - Once you see "Deploy live ✓" you're good!

### Step 4: Test Your Deployment

Your app will be live at:
```
https://permit-converter.onrender.com
```

Test it:
1. Open the URL in browser
2. Upload one of your test permits
3. Verify GPS links work

### Step 5: (Optional) Custom Domain

**Free Option:**
- Use the Render URL: `permit-converter.onrender.com`

**Paid Option ($10-15/year):**
1. Buy domain (e.g., permitgps.com on Namecheap)
2. In Render dashboard: Settings → Custom Domain
3. Add your domain
4. Update DNS records as shown
5. Wait 10-60 mins for SSL

---

## Alternative: Deploy to Heroku

### If you prefer Heroku:

1. **Sign up at heroku.com**

2. **Install Heroku CLI** (on your computer)
   ```bash
   # Mac
   brew install heroku/brew/heroku
   
   # Windows
   # Download from heroku.com
   ```

3. **Deploy**
   ```bash
   heroku login
   heroku create permit-converter
   git push heroku main
   heroku open
   ```

**Note:** Heroku charges $5/month now (no free tier)

---

## Alternative: Deploy to Railway.app

### Fast & Simple (Good Free Tier)

1. Go to https://railway.app
2. Sign in with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your repo
6. Railway auto-detects Python
7. Deploy happens automatically
8. Get URL: `permit-converter.up.railway.app`

---

## Alternative: Deploy to Vercel (Serverless)

### For serverless deployment:

1. Install Vercel CLI
   ```bash
   npm i -g vercel
   ```

2. Create `vercel.json`:
   ```json
   {
     "builds": [
       {
         "src": "api_server.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "api_server.py"
       }
     ]
   }
   ```

3. Deploy
   ```bash
   vercel --prod
   ```

---

## 🎯 Which Platform Should You Choose?

| Platform | Free Tier | Best For | Setup Time |
|----------|-----------|----------|------------|
| **Render** | ✅ Yes (sleeps after 15min) | MVP testing | 10 min |
| Railway | ✅ Yes ($5 credit/month) | Quick deploy | 5 min |
| Heroku | ❌ $5/month | Production | 15 min |
| Vercel | ✅ Yes | Serverless | 10 min |

**Recommendation: Start with Render.com** - it's free, reliable, and easy.

---

## 📊 What Happens After Deploy?

### 1. Your App is Live
- Users can visit: `https://your-app.onrender.com`
- Upload permits
- Get GPS links
- Works on mobile

### 2. Monitor Usage
- Render dashboard shows:
  - Number of requests
  - Response times
  - Errors
  - Memory usage

### 3. Limitations (Free Tier)
- ⚠️ **Sleeps after 15 min of inactivity**
  - First request takes 30-60 seconds to wake
  - Fine for testing, annoying for users
- Limited to 750 hours/month (plenty for MVP)
- 512MB RAM (enough for this app)

### 4. When to Upgrade
Upgrade to paid ($7/month) when:
- You have 5+ daily users
- Sleep time becomes annoying
- Need faster response times
- Want custom domain with SSL

---

## 🔧 Troubleshooting

### App won't start?
- Check Render logs for errors
- Verify `requirements.txt` installed
- Make sure `Procfile` is correct

### Can't upload PDFs?
- Check file size limit (Render: 100MB default)
- Verify CORS is enabled
- Check browser console for errors

### GPS links don't work?
- Test with your sample permits first
- Check parser output in logs
- Verify Google Maps URLs are valid

### Deploy failed?
- Make sure all files are in repo
- Check Python version (should be 3.8+)
- Review build logs in Render

---

## ⚡ Quick Commands

**View logs:**
```bash
# In Render dashboard: Logs tab
# Shows real-time requests and errors
```

**Redeploy:**
```bash
# Just push to GitHub
git add .
git commit -m "Update parser logic"
git push

# Render auto-deploys
```

**Environment variables:**
```bash
# In Render: Environment tab
# Add: DEBUG=False for production
```

---

## 🎉 Success Checklist

After deployment, verify:

- [ ] App loads at Render URL
- [ ] Can upload a test permit PDF
- [ ] Parser extracts route correctly
- [ ] Google Maps link opens with route
- [ ] Apple Maps link works on iPhone
- [ ] Works on mobile browser
- [ ] No errors in Render logs

Once all checked → **You're live!** 🚀

---

## 📱 Next: Share It

1. Test with your own permits
2. Send link to 2-3 dispatcher friends
3. Ask for feedback
4. Iterate based on real usage
5. Add pricing when ready

**Your app is now on the internet. Anyone can use it.** That's the power of deployment! 🎯
