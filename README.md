Band Saw: Log monitoring and alerting for the GNOME Desktop
===========================================================

Band Saw is a syslog monitoring program that I wrote for the GNOME desktop, back in 2004.

At the time I led the development team at Cmed Technology, and we needed to keep tabs on a rather complicated distributed system, running on hundreds of servers and (remote) laptops.

This was in the days before the cloud and "observability" was a thing, and we had to roll our own solution. We built a really useful monitoring system on top of the Unix Syslog daemon, that gave the support immediate insight into any problems that our customers were experiencing.

The Syslog daemons on our servers and laptops forwarded any error messages to a central server, that then dispatched them to the workstations of the support staff and development team.

Band Saw was setup to keep an eye out for those incoming error messages.

Here's the main window, showing messages that contain the word "test":

<img src="./htdocs/images/ss/bandsaw.png?raw=true" alt="Band Saw's main window" class="screenshot">

We could configure filters that would ensure that any errors occurring within the system were brought to our attention. We could also define filters to ignore errors that we'd already dealth with, but for which the fix hadn't yet been deployed.

<img src="./htdocs/images/ss/preferences.png?raw=true" alt="Configuring Band Saw's filters" class="screenshot">

If a message came in that warranted our immediate attention, Band Saw would let us know by blinking an icon in our system tray. Clicking the icon would show us the log message.

<img src="./htdocs/images/ss/alert.png? raw=true" alt="Band Saw's alert dialog" class="screenshot">

It changed the game for those of us supporting a massive distributed system. **Rather than users coming to us with a problem, we could walk up to their desk with a solution**, often before they'd even noticed that they'd encountered a bug.

For more on the backstory (and how we used Syslog) see the [full write-up] on my blog.

Band Saw is written in Python, and uses the PyGTK wrappers for the GTK+ graphical toolkit.

The [htdocs](./htdocs) directory contains the source code for the statically generated web site, that was [hosted on SourceForge] (in case you're not familiar, SourceForge was what we all used before GitHub). Yep, SSG was a thing. And all you need is a `Makefile`. ;-)

[hosted on SourceForge]: https://sourceforge.net/projects/bandsaw
[full write-up]: https://effectif.com/projects/bandsaw
