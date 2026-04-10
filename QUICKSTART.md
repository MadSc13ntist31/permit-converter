# ⚡ QUICK START - Deploy in 15 Minutes

## You Have Everything You Need ✅

All files are in `/mnt/user-data/outputs/`:
- ✅ api_server.py
- ✅ parse_permit.py  
- ✅ permit_converter_app.html
- ✅ requirements.txt
- ✅ Procfile
- ✅ README.md
- ✅ DEPLOYMENT.md

## 3-Step Deploy (15 minutes)

### Step 1: GitHub (5 min)

1. Download all files from `/mnt/user-data/outputs/`
2. Go to https://github.com/new
3. Create repo: `permit-converter`
4. Upload all 7 files
5. Commit

**OR use Git CLI:**
```bash
cd permit-converter
git init
git add .
git commit -m "Initial deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/permit-converter.git
git push -u origin main
```

### Step 2: Render.com (5 min)

1. Sign up at https://render.com (use GitHub)
2. Click "New +" → "Web Service"
3. Select your `permit-converter` repo
4. Configure:
   - **Name:** permit-converter
   - **Runtime:** Python 3
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `gunicorn api_server:app`
   - **Plan:** Free
5. Click "Create Web Service"

### Step 3: Test (5 min)

1. Wait for "Deploy live ✓" (~3-5 min)
2. Click your app URL (e.g., `permit-converter.onrender.com`)
3. Upload one of your test permits
4. Verify GPS links work
5. Test on phone

## Done! 🎉

Your app is LIVE on the internet!

Share the link:
```
https://permit-converter.onrender.com
```

---

## Troubleshooting

**Build failed?**
- Check you uploaded ALL files
- Verify requirements.txt is present
- Look at build logs in Render

**App won't load?**
- Wait 30 seconds (free tier wakes from sleep)
- Check runtime logs for errors
- Verify PORT environment variable

**Can't upload PDFs?**
- Check file size (<10MB recommended)
- Try different PDF
- Check browser console (F12)

---

## Next Steps

✅ **App is deployed!**

Now:
1. Test with 5-10 different permits
2. Send link to 2 dispatcher friends
3. Collect feedback
4. Fix any parsing issues
5. Add email submission (Week 2)
6. Launch paid tier (Week 4)

---

## Important Notes

**Free Tier Limits:**
- App sleeps after 15min inactivity
- First request takes ~30 sec to wake
- Fine for testing, upgrade for production

**Upgrade when:**
- You have 5+ daily users
- Sleep time is annoying
- Ready to charge money

**Cost:**
- Free tier: $0/month
- Starter: $7/month (no sleep, faster)
- Professional: $25/month (more RAM, scaling)

---

## Need Help?

Read the detailed guide:
- See DEPLOYMENT.md for troubleshooting
- See README.md for architecture details

**You've got this! 🚀**
