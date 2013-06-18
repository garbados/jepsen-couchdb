# Run-DMC explains Network Partitions

[![It's Tricky.][tricky_cover]][tricky]

**Networks are tricky**

Run-DMC knows how it is. Fools think, hey, I give the database my data; it should be there when I want it, right? Not so fast. As Rev. Run says, "It's very complicated."

Inspired by Kyle Kingsbury's [Jepsen][jepsen] series, this is my attempt to put CouchDB through the same rigorous testing to uncover just how tricky distributed systems are.

**Sing along**

To run these tests yourself, you'll need a cluster of CouchDB machines. To do that, I just installed five copies of CouchDB and configured them to use different ports. To do that, we'll compile CouchDB from source, so we'll need to install CouchDB's dependencies. 

If you're on Unix, read [this](https://raw.github.com/apache/couchdb/master/INSTALL.Unix). If you're on Windows, read [this](https://raw.github.com/apache/couchdb/master/INSTALL.Windows). Once you've got all the necessary dependencies:

    git clone git@github.com:apache/couchdb.git
    cd couchdb
    ./bootstrap

Then, for each of your five copies, do this:

    ./configure --prefix=/absolute/path/to/copy/directory/n1
    make && make install

...Where for each copy, n1 becomes n2, n3, n4, etc. Then, for each copy, go to wherever you installed it, and edit `etc/couchdb/default.ini`. Find the section that looks like...

    [httpd]
    port = 5984
    bind_address = 127.0.0.1
    
...and make it look like...

    [httpd]
    port = 5985
    bind_address = 127.0.0.1

...where for n1 it's 5, for n2 it's 6, etc., so that each copy uses a different port. In the end, you should be using ports 5985 - 5989.

To start each copy, run `bin/couchdb`, such as by going to the root of the copy (the place specified earlier in the `prefix` argument) and executing:

    ./bin/couchdb

Once you've got your cluster:

    git clone git@github.com:garbados/jepsen-couchdb.git 
    cd jepsen-couchdb
    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt

Now you should be good to go.

**Clusters in CouchDB**

CouchDB isn't built to operate in clusters by default, so for this experiment, our five nodes just replicate between each other, aspiring to be identical.

Continuous replication in CouchDB sets up a listener on the source database's changes feed, and pushes changes to the source database as they occur. If the replication fails at any point, it retries a configurable number of times in lengthening intervals, until eventually it gives up.

Each node in our cluster replicates with every other node, so the network map looks like this:

![Pentalicious][pentagram]

That way, if a node ever loses connection, then replications will bring it up-to-date once it comes back -- assuming it's offline for less time than it takes for the replication to stop retrying the connection, which by default is a few days.

**Rock a Rhyme: Simple Writes**

First, let's see what happens if we just write a bunch of numbers to our cluster. Do...

    python test.py simple sequential

...and you should see something like this:

    Reset.
    Synced.
    100 writes total.
    100 writes acknowledged.
    20 writes written to node 5985
    40 writes written to node 5986
    100 writes written to node 5987
    ...and checksum passes!
    100 writes written to node 5988
    ...and checksum passes!
    100 writes written to node 5989
    ...and checksum passes!
    Reset.

Two of our five nodes don't have all the writes they should, since by the time we query each of them, they're still replicating. In other words, even under normal conditions, our nodes find themselves in an inconsistent state.

But if we check back in five seconds, with `python test.py sleep sequential`, you see...

    Reset.
    Synced.
    100 writes total.
    100 writes acknowledged.
    100 writes written to node 5985
    ...and checksum passes!
    100 writes written to node 5986
    ...and checksum passes!
    100 writes written to node 5987
    ...and checksum passes!
    100 writes written to node 5988
    ...and checksum passes!
    100 writes written to node 5989
    ...and checksum passes!
    Reset.

Everything's consistent. All it took was time. But that means anywhere in those five seconds, queries to the cluster would return inconsistent results: one node saying a doc doesn't exist when another says it does, etc. How can we fix this?

**My name is Run, I'm \#1: Master Writes**

Many databases have a master-slave setup, where writes go to the master, which replicates to numerous slaves, which handle reads. We can do this with our current setup by running `python test.py simple direct`, which yields:

    Reset.
    Synced.
    100 writes total.
    100 writes acknowledged.
    100 writes written to node 5985
    ...and checksum passes!
    100 writes written to node 5986
    ...and checksum passes!
    100 writes written to node 5987
    ...and checksum passes!
    100 writes written to node 5988
    ...and checksum passes!
    100 writes written to node 5989
    ...and checksum passes!
    Reset.

(Why does this happen? I don't know D:) Hey, it worked! Nice as this is, you can run into scaling issues as clients become geographically distributed. If you want multiple, geographically distributed masters so that your users in China and Zimbabwe don't experience prohibitive lag with your Chicago master, you slowly but surely approach the same consistency problems we hit in the first place. That's no good.

**We don't quit: Quorum**

Since we wrote our doc to a node in the cluster, then we know at least one node has the document. [Quorum][quorum] is a technique for handling this circumstance, which queries multiple nodes and uses their responses as "votes". When a particular result has enough votes, it's returned to the client. If the cluster can't reach quorum, such as by nodes disagreeing, the client gets an error saying so.

We can aggregate the results of our randomly-distributed writes to get everything we wrote, even though no single node may have everything, by running `python test.py quorum sequential`, which should print this:

    Reset.
    Synced.
    100 writes total.
    100 writes acknowledged.
    Got 3b7dbb7025f09af25e40a41d5347e028 by quorum!
    100 docs in result set.
    ...and checksum passed!
    Reset.

That `Got [id] by quorum!` line refers to a function in the check that has multiple nodes vote on their version of a doc. If no version has a majority, the function reports that getting the document failed. That's quorum.

**Right on time: Application Design**

Quorum reduces the probability our system is inconsistent during a transaction, but it doesn't solve the problem. Even if a majority of nodes agree, it might be that the up-to-date nodes are just in the minority. CouchDB is an AP system, so as long as the CAP theorem holds, our data is only eventually consistent.

Inconsistency is most problematic when updating documents: you write a doc, succeed, go to update it, and find the cluster telling you it doesn't exist. A simple solution is, well, don't update your docs. Write new ones instead.

[Sam Bisbee][sbisbee] related this design philosophy to me through the lens of the accountant's ledger: when new financial transactions occur, you don't go back and change old lines, you just write new ones. Totals are then calculated dynamically, by summing rows.

This view makes considerable use of CouchDB's secondary indexes to slice and dice data into what you need. In essence, keep your docs merely as data. Use MapReduce to derive meaning from them.

The only time it makes sense, then, to update a record is when it's incorrect, or if you're migrating to a new schema. Writing application logic that embraces this will save you a thousand headaches.

**Dissed her and dismissed her: Breaking the Cluster**

Back to testing: let's blow up a node. Run `python test.py simple direct` again, but kill  the n1 node as writing begins. (CTRL-C should do the trick) You should get results like this:

    Reset.
    Synced.
    100 writes total.
    100 writes acknowledged.
    5985 down :(
    96 writes written to node 5986
    96 writes written to node 5987
    96 writes written to node 5988
    96 writes written to node 5989

As expected, requests failed over to using n2 as a master, but we lost any writes on n1 that hadn't replicated over by the time we killed it. We could write docs to multiple nodes at once, but they would have no way of reconciling that those docs are the same, so we'd end up with duplicates. That's no good.

[Cloudant][cloudant]'s implementation of BigCouch -- a CouchDB derivative -- handles this through sharding. BigCouch is slated to be merged back in Q4 2013, so eventually vanilla CouchDB will enjoy such fault tolerance.

In the meantime, the best we can do is rely on master-master replication to provide fault tolerance. Try `python test.py quorum sequential`, and kill a node mid-test again. You should get this:

    Reset.
    Synced.
    100 writes total.
    100 writes acknowledged.
    Got 15e193f8b86ad7f3a4fcdd06771ddf0a by quorum!
    100 docs in result set.
    ...and checksum passed!

`sequential` evenly distributes our workload over the cluster, diminishing the number of writes on each node at any given time, and thus reducing the number likely to be lost if a node dies. But, this only reduces the chance - it doesn't eliminate it.

**Always tearin' what I'm wearin': Partitioning the Network**

Now the fun. We'll split our 5-node cluster into two parts: n1-n2, and n3-n5. We do this by restricting who replicates with who.

First, try `python test.py sleep sequential part_network` to see what happens when we go at these partitions normally:

    Reset.
    Synced. # syncing n1-n2
    Synced. # syncing n3-n5
    100 writes total.
    100 writes acknowledged.
    40 writes written to node 5985
    40 writes written to node 5986
    60 writes written to node 5987
    60 writes written to node 5988
    60 writes written to node 5989
    Reset.

That makes sense. `sequential` made sure each node got 20% of the total workload, so that 40/60 split reflects each partition replicating amongst itself. If we try `python test.py quorum sequential part_network`, the news is even better:

    Reset.
    Synced.
    Synced.
    100 writes total.
    100 writes acknowledged.
    Got 302d54e96d034eb503dc4a4e7c290b9e by quorum!
    100 docs in result set.
    ...and checksum passed!
    Reset.

This is only possible because we're not performing updates, only new writes. If we were, nodes would conflict and somebody would lose data. So, protip: prefer writes over updates wherever possible.

**Raising Hell: Updates**

This was my first ops-style project, and coming from a dev background, I found it illuminating. Vanilla CouchDB performed better than I'd expected, but so much of that depended on design patterns. If I'd thrown updates into the mix, this would have been a shitshow.

But... that's what you came to see, isn't it? Run `python test.py shitshow shitshow part_network`:

    Reset.
    Synced.
    Synced.
    100 writes total.
    100 writes acknowledged.
    Counter({u'2-ac64b21093c8c7f03366886641819bc7': 2})
    Failed to get e5b8e5442fbd3c191eb5a43f2337457b by quorum
    100 docs in result set.
    Reset.

So, our client thinks every write succeeded. And the cluster does only have 100 documents on it. But the doc we tried to find lived on the minority partition; due to quorum constraints, every document on the minority partition is inaccessible. That's **40% data loss**.

Gross.

What happens when we allow the partition to recover? Try `python test.py heal shitshow part_network`:

    Reset.
    Synced.
    Synced.
    100 writes total.
    100 writes acknowledged.
    Counter({u'2-efe983e9ba94f532dc75238b07af8605': 2})
    Failed to get c06651b5ba697a09054ae6bd8f183c4d by quorum
    100 docs in result set.
    ...and checksum passed!
    Synced. # partitions recover; we wait 5 seconds for them to heal
    100 writes written to node 5985
    ...and checksum passes!
    100 writes written to node 5986
    ...and checksum passes!
    100 writes written to node 5987
    ...and checksum passes!
    100 writes written to node 5988
    ...and checksum passes!
    100 writes written to node 5989
    ...and checksum passes!
    Got 15e193f8b86ad7f3a4fcdd067738fb1d by quorum!
    Reset.

Not bad. When we allow the network to recover, the nodes come together again. No duplicates. Checksums pass. And we get our doc by quorum! Whoo!

**Final Thoughts**

Per the question on Jepsen's [Final Thoughts][final] post, "How do computers even work?" I still sit firmly in the camp of those who have no idea. But by asking questions, testing assumptions, and listening to lots of [Run-DMC remixes](http://www.youtube.com/watch?v=mGEJMmzKviY), I feel like I've come closer to understanding.

CouchDB isn't built to handle clusters, so much of how this cluster chose to do so was by my own design, but given dangerously little effort, it performed admirably.

The trouble caused by updates reinforced the design patterns impressed on me by the team at [Cloudant][cloudant], while master-master replications allowed the cluster to endure better than other popular NoSQL databases did under Jepsen's punishment.

Thanks again to Kyle for the Jepsen series. You inspired me to learn more by breaking stuff -- the best kind of learning.

[jepsen]: http://aphyr.com/posts/281-call-me-maybe-carly-rae-jepsen-and-the-perils-of-network-partitions
[tricky]: http://www.youtube.com/watch?v=l-O5IHVhWj0
[tricky_cover]: http://www.bitcandy.com/img/plogs/1334080668.jpg
[pentagram]: http://farm3.staticflickr.com/2854/9067722628_09560c77ae_o.jpg
[quorum]: http://en.wikipedia.org/wiki/Quorum_(distributed_computing)
[sbisbee]: http://www.sbisbee.com/
[final]: http://aphyr.com/posts/286-call-me-maybe-final-thoughts
[cloudant]: https://cloudant.com/