# Run DMC explains Network Partitions

[![It's Tricky.][tricky_cover]][tricky]

## Networks are tricky

Run DMC knows how it is. Fools think, hey, I give the database my data; it should be there when I want it, right? Not so fast. As Rev. Run says, "It's very complicated."

Inspired by Kyle Kingsbury's [Jepsen][jepsen] series, this is my attempt to put CouchDB through the same rigorous testing to uncover just how tricky distributed systems are.

## Sing along

To run these tests yourself, you'll need a cluster of CouchDB machines. To do that, I just installed five copies of CouchDB and configured them to use different ports. Here's how to do that:

    ...

Once you've got your cluster, clone this repo and `make install`.

## Clusters in CouchDB

CouchDB isn't built to operate in clusters by default, so for this experiment, our five nodes just replicate between each other, aspiring to be identical. To set up that replication, do `make build`.

Continuous replication in CouchDB polls a target database for changes every few seconds, and pulls them into the source database. If the replication fails at any point, it retries a configurable number of times in lengthening intervals, until eventually it gives up.

Each node in our cluster replicates with every other node, so the network map looks like this:

![Pentalicious][pentagram]

That way, if a node ever loses connection, then replications will bring it up-to-date once it comes back -- assuming it's offline for less time than it takes for the replication to stop retrying the connection, which by default is a few days.

## Rock a Rhyme: Simple Writes

First, let's see what happens if we just write a bunch of numbers to random nodes. Do...

    make clean && make build && python test.py simple random

...and you should see something like this:

    python reset.py
    Reset.
    python sync.py
    Synced.
    100 writes total.
    100 writes acknowledged.
    15 writes written to node 5985
    39 writes written to node 5986
    99 writes written to node 5987
    100 writes written to node 5988
    ...and checksum passes!
    100 writes written to node 5989
    ...and checksum passes!

Three of our five nodes don't have all the writes they should, since by the time we query each of them, they're still replicating. In other words, even under normal conditions, our nodes find themselves in an inconsistent state.

But if we check back in five seconds, with `make clean && make build && python test.py sleep random`, you see...

    python reset.py
    Reset.
    python sync.py
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

Everything's consistent. All it took was time. But that means anywhere in those five seconds, queries to the cluster would return incosistent results: one node saying a doc doesn't exist when another says it does, etc. How can we fix this?

## My name is Run, I'm \#1: Master Writes

Many databases have a master-slave setup, where writes go to the master, which replicates to numerous slaves, which handle reads. We can do this with our current setup by running `make clean && make build && python test.py simple direct`, which yields:

    python reset.py
    Reset.
    python sync.py
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

(Why does this happen? I don't know D:) Hey, it worked! Nice as this is, you can run into scaling issues as clients become geographically distributed. If you want multiple, geographically distributed masters so that your users in China and Zimbabwe don't experience prohibitive lag with your Chicago master, you slowly but surely approach the same consistency problems we hit in the first place. So, we need something better.

## We don't quit: Quorum

Since we wrote our doc to a node in the cluster, then we know at least one node has the document. [Quorum][quorum] is a technique for handling this circumstance, which queries multiple nodes and uses their responses as "votes". When a particular result has enough votes, it's returned to the client. If the cluster can't reach quorum, such as by nodes disagreeing, the client gets an error saying so.

We can aggregate the results of our randomly-distributed writes to get everything we wrote, even though no single node may have everything, by running `make clean && make build && python test.py quorum random`, which should print this:

    python reset.py
    Reset.
    python sync.py
    Synced.
    100 writes total.
    100 writes acknowledged.
    Got 3b7dbb7025f09af25e40a41d5318438f by quorum!
    100 docs in result set.
    ...and checksum passed!

That `Got [id] by quorun!` line refers to a function in the check that has multiple nodes vote on their version of a doc. If no version has a majority, the function reports that getting the document failed. That's quorum.

## Right on time: Application Design

Inconsistency is especially problematic if you're trying to update documents: you write a doc, succeed, go to update it, and find the cluster telling you it doesn't exist. A simple solution is, well, don't update your docs. Write new ones instead.

Sam Bisbee related this design philosophy to me through the lense of the accountant's ledger. 

[jepsen]: http://aphyr.com/posts/281-call-me-maybe-carly-rae-jepsen-and-the-perils-of-network-partitions
[tricky]: http://www.youtube.com/watch?v=l-O5IHVhWj0
[tricky_cover]: http://www.bitcandy.com/img/plogs/1334080668.jpg
[pentagram]: http://farm3.staticflickr.com/2854/9067722628_09560c77ae_o.jpg
[quorum]: http://en.wikipedia.org/wiki/Quorum_(distributed_computing)