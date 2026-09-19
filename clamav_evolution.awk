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

BEGIN { active = "" }
{
    sub(/\r$/, "")
    if ($0 == "") exit
    if ($0 ~ /^[ \t]/) {
        if (active != "") {
            sub(/^[ \t]+/, "")
            value[active] = value[active] " " $0
        }
        next
    }
    active = ""
    colon = index($0, ":")
    if (!colon) next
    name = tolower(substr($0, 1, colon - 1))
    if ((name == "from" || name == "subject") && !(name in seen)) {
        seen[name] = 1
        text = substr($0, colon + 1)
        sub(/^[ \t]+/, "", text)
        value[name] = text
        active = name
    }
}
END {
    if ("from" in seen) printf "From: %s\n", value["from"]
    if ("subject" in seen) printf "Subject: %s\n", value["subject"]
}
