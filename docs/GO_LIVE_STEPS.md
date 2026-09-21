# Go-live steps

Four things only you can do, in the order that avoids doing anything twice. About 30 minutes in total.

## 1. Rotate the database password (10 minutes)

Do this first so the new password goes into every place once.

1. Open the Supabase dashboard, pick the Vantage project, then **Project Settings > Database**.
2. Under **Database password**, click **Reset database password**. Let it generate one, or type a long one of your own.
   Copy it somewhere safe for a minute. Do not paste it into chat or a file in the repository.
3. In PowerShell, from `C:\Users\welln\vantage\apps\api`, run:

   ```powershell
   .venv\Scripts\python -m app.vercel_env --ref xcczkaaytuqyhnhzlcge
   ```

   It asks for the password (nothing shows as you type) and rewrites `apps\api\.env.vercel` with a fresh connection string.
   It keeps the same signing key, so nobody is logged out.
4. Put the new connection string into Vercel:
   - Vercel dashboard > **vantage-api** > **Settings** > **Environment Variables**.
   - Find `DATABASE_URL`, open the three dots, **Edit**, paste the new value, **Save**.
   - Go to **Deployments**, open the latest one, three dots, **Redeploy**.
5. Check it: open `https://vantage-api-nu.vercel.app/health`. You should see `"status":"ok"`.
6. When everything below works, delete `apps\api\.env.vercel`. It holds the password in plain text.

## 2. Give GitHub the connection string, then fetch fresh stories (5 minutes)

1. Copy the connection string to the clipboard without showing it (from `C:\Users\welln\vantage`):

   ```powershell
   (Get-Content apps\api\.env.vercel | Select-String '^DATABASE_URL=').Line.Substring(13) | Set-Clipboard
   ```

2. On GitHub open the repository **saikrishnagopalveluri/Vantage**, then **Settings > Secrets and variables > Actions**.
3. **New repository secret**. Name: `DATABASE_URL`. Secret: paste. **Add secret**.
4. Open the **Actions** tab, choose **ingest** on the left, **Run workflow**, keep `hourly`, **Run workflow**.
5. Open the run when it appears. It takes two to five minutes. The log ends with how many stories were added.
6. Check the site: `https://vantage-api-nu.vercel.app/public/pulse` should now show `stories_today` above 0.
   After that the workflow runs by itself every hour.

If the run fails with a connection error, the secret has the wrong string. Repeat step 1 and update the secret.

## 3. Fill in the legal pages (10 minutes, plus review)

1. Vercel > **vantage-api** > **Settings** > **Environment Variables**. Add these for Production:

   | Name | What to put |
   | --- | --- |
   | `VANTAGE_OPERATOR_NAME` | The person or company that runs Vantage, as it should appear in the terms |
   | `VANTAGE_CONTACT_EMAIL` | An inbox you read, for privacy requests |
   | `VANTAGE_GRIEVANCE_OFFICER` | Name of the person who handles complaints (under the DPDP Act this must be a named contact) |
   | `VANTAGE_GRIEVANCE_EMAIL` | Optional. Leave out to reuse the contact email |
   | `VANTAGE_POSTAL_ADDRESS` | Optional, but a real postal address makes the notice more complete |
   | `VANTAGE_HOSTING_REGION` | Where the data sits, for example `Tokyo, Japan (Supabase and Vercel)` |

2. **Redeploy** the API (Deployments > latest > Redeploy).
3. Open `https://vantage-web-vert.vercel.app/privacy`. "Not set yet" should be gone.

**Legal review.** I am not a lawyer and the pages are a draft. Send a lawyer who knows India's Digital Personal Data
Protection Act, 2023 (and the GDPR if you will have readers in Europe) these three things:

- the live `/terms` and `/privacy` pages,
- the list of what Vantage stores (sign in, then **Profile > Your data > Download**, which gives a real example),
- the fact that readers must be 18 or older, and that guests are stored by a random device id.

Ask them specifically about the age gate, the consent wording, how long you keep data, and the grievance process.

## 4. Try Listen on your phone and laptop (5 minutes)

Open a story on the Feed, tap **Summary and pointers**, then **Listen**. Switch between **Female** and **Male**, and change the speed.

The voices come from the device, so they sound different on each one:

- **Windows laptop:** use Microsoft Edge. It offers the natural voices (Aria, Guy, Neerja, Prabhat), which sound far better than
  the older ones in Chrome. To add more: Settings > Accessibility > Narrator > Add natural voices.
- **iPhone or Mac:** Settings > Accessibility > Spoken Content > Voices > English. Download a voice marked **Enhanced** or **Premium**
  (for example Ava or Zoe).
- **Android:** Settings > System > Languages > Text-to-speech output. Install the English (India) or English (UK) voice data.

Tell me which voices you liked, and which sounded wrong, and I will tune the picker.
