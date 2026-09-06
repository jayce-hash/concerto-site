# Concerto Partner Forms - one-time Netlify setup

The partner forms use Netlify Forms so no founder/personal email address appears in the markup. Netlify captures every submission.

After the first deploy:
1. Open the Concerto site in Netlify.
2. Go to Forms and confirm these forms are detected: partner-restaurants-interest, partner-hotels-interest, partner-venues-interest, partner-artists-interest.
3. In Form notifications, add an Email notification to `partnerships@concertocity.com` for each partner form (or an account-wide form notification if preferred).
4. Optionally route `general-company-contact` notifications to the public company/support workflow you want to use.

The site intentionally contains no personal founder email address after this patch.
