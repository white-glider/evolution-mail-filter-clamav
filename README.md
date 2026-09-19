# evolution-mail-filter-clamav

External e-mail filter for [Evolution](https://help.gnome.org/users/evolution/stable/) mail client that scans messages for viruses using [ClamAV](https://www.clamav.net/) anti-virus.

## Prerequisites

This filter was written in [BASH](https://www.gnu.org/software/bash/) and [AWK](https://www.gnu.org/software/gawk/), which should come pre-installed on most Linux distributions. It depends on ClamAV (`clamscan`) and [Gnome's libnotify](https://gnome.pages.gitlab.gnome.org/libnotify/) (`notify-send`).

It was successfully tested on:
1. [Ubuntu](https://ubuntu.com/desktop) 22.04.4 LTS (jammy) running Evolution 3.44.4, GNU BASH 5.1.16, MAWK 1.3.4, ClamAV 0.103.11  and libnotify 0.7.9.
2. [Fedora](https://getfedora.org/) 28 Workstation running Evolution 3.28.5, GNU BASH 4.4.23, GNU AWK 4.2.1, ClamAV 0.100.1 and libnotify 0.7.7.

Notifications use the standard `dialog-warning` icon name. Instructions on how to install ClamAV can be found [here](https://docs.clamav.net/manual/Installing.html). Keep its signature database updated with FreshClam. GNU coreutils (`mktemp`, `readlink`, `cat`, `rm`) are also required.

## Installing

Note: the brief instructions below assume the reader has some basic knowledge of how to use a Linux system.

Simply copy **both** scripts from this project (`.sh` and `.awk`) into a directory of your choice (suggestion: `${HOME}/bin`), set the execute permission on the `.sh` script (e.g. `chmod u+x clamav_evolution.sh`), and add a new message filter for incoming mail to Evolution which pipes messages to the `.sh` script (see [here](https://help.gnome.org/users/evolution/stable/mail-filters.html.en) for more information):

![Screenshot of Evolution filter](images/filter_screenshot.png)

You might want to create a new subfolder under your INBOX to where the messages caught by this filter would be moved (suggestion: Quarantine).

The script returns **0** only after a clean scan, **1** when a threat is found,
and **2** when scanning cannot be completed. Configure Evolution to also flag
or move messages whose pipe-program status is **2** into a separate folder for
manual review. A filter matching only status 1 will not catch scan failures.
The script reports errors but does not itself move or delete messages.

## Testing

You can use [EICAR's standard anti-virus test files](https://www.eicar.org/download-anti-malware-testfile/) to see if the script works. For instance:

```
$ cat eicar.com | clamav_evolution.sh
```

You should see a desktop notification like the one below:

![Desktop notification](images/notification_screenshot.png)

To run the automated regression suite (Python 3.10+ and Bash required):

```sh
python3 -m unittest discover -s tests -v
bash -n clamav_evolution.sh
shellcheck clamav_evolution.sh
```

Tests use harmless scanner/notifier stubs. Linux tests additionally check
private file permissions and cleanup after SIGTERM. They do not replace a
manual check of Evolution's filter rules and desktop notifications.

## Usage

After enabling the new message filter in Evolution, every new email that arrives at your INBOX will be automatically sent to the shell script, which in turn will send it to ClamAV. If ClamAV finds a threat then the script will send you a desktop notification.

In fact, the shell script only acts as liaison between Evolution and ClamAV. The AWK script is just for parsing the email message and extract the fields `From` and `Subject` to enrich the desktop notification so it's easier to identify which message contains the threat.

Messages and results are stored in a private, randomly named directory under
`${TMPDIR:-/tmp}` and removed on normal exit and handled HUP/INT/TERM signals.
SIGKILL, power loss, and system crashes cannot run cleanup traps. Notification
failure is logged to stderr and does not turn a detection or scan error into
success. Header parsing stops at the body, accepts case-insensitive field names
and unfolds continuation lines.

## Tweaks

There are a few things that you might want to change in the shell script depending on how many emails you receive or how dramatic you want the threat notification to be. See below:

* `clamdscan` may reduce per-message startup overhead, but it requires a configured daemon with access to the input. It is not a drop-in replacement for the current command and its `clamscan` options; adapt and test it separately.
* More visible threat notifications can be achieved by replacing `notify-send` with [`zenity`](https://gitlab.gnome.org/GNOME/zenity) (Gnome) or [`kdialog`](https://invent.kde.org/utilities/kdialog) (KDE).

## Limitations

Currently the script can't decode "encoded-words" if they are used in email headers, therefore any notifications triggered by emails that contain those "encoded-words" (e.g. in the subject line) will display their encoded form. Note that the virus detection works as usual and it's not affected by this limitation.

Please refer to [RFC1522](https://tools.ietf.org/html/rfc1522) for more information.

## Alternatives

ClamAV now has [on-access scanning](https://docs.clamav.net/manual/OnAccess.html) capabilities which might be interesting to explore if you are tech savvy, but note that [there was some criticism about its stability](https://wiki.archlinux.org/title/ClamAV#OnAccessScan). I personally haven't tested it.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
