# Change request: nightly closed-ticket export

From: Dana Whitfield, Finance Operations
To: Platform team

We calculate SLA credits for closed support tickets, and right now we pull
them by hand from the helpdesk app every morning. Can we get a nightly CSV
of closed tickets dropped into our finance exports bucket instead? The job
that builds the credit report runs at 3 AM Eastern, so the file needs to be
there before then.

We only need the fields we use for credits: the ticket, who raised it, its
priority, when it was opened, and when it was closed.

Please keep access tight. The export should only be able to read tickets
and write to our bucket, nothing else.

Thanks,
Dana
