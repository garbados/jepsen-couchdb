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

[![Pentalicious][pentagram]]

That way, if a node ever loses connection, then replications will bring it up-to-date once it comes back -- assuming it's offline for less time than it takes for the replication to stop retrying the connection, which by default is a few days.

## Rock a Rhyme: Simple Writes

First, let's see what happens if we just write a bunch of numbers to random nodes. Do `make check` and you should see something like...

    ...

Some or even all nodes may not have all writes, since by the time we query each of them, they're still replicating. In other words, even under normal conditions, our nodes find themselves in an inconsistent state.

But if we check back in five seconds, with `make sleep`, you see...

    ...

Everything's consistent. All it took was time. But that means anywhere in those five seconds, queries to the cluster would return incosistent results: one node saying a doc doesn't exist when another says it does, etc. How can we fix this?

[jepsen]: http://aphyr.com/posts/281-call-me-maybe-carly-rae-jepsen-and-the-perils-of-network-partitions
[tricky]: http://www.youtube.com/watch?v=l-O5IHVhWj0
[tricky_cover]: http://www.bitcandy.com/img/plogs/1334080668.jpg
[pentagram]: http://farm3.staticflickr.com/2854/9067722628_09560c77ae_o.jpg