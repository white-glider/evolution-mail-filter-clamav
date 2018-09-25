BEGIN { from=subj="" }
{
	if (match($0, "^From: ")) {
		if (!from) from=substr($0, RSTART) "\n"
		next
 	} else if (match($0, "^Subject: ")) {
		if (!subj) subj=substr($0, RSTART) "\n"
		next
	}
	if (from && subj) exit
}
END { printf("%s%s", from, subj) }
