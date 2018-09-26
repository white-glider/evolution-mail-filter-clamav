# Copyright (c) 2018 Felix Almeida (white-glider)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

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
