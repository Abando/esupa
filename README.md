# Esupa #

Esupa stands for Event Subscription and Payment, and it's meant to handle collection of attendee data and payment for events that are just big enough for Google Forms and manual deposits being insufficient.

It's created for [Abando](http://www.abando.com.br/), an anual event in Brazil, but we hope this can be universally useful.

### Prerequisites ###

* Python 3
* Django 1.8

### How do I get set up? ###

* [Install Python 3](https://www.python.org/downloads/)
```
#!sh

sudo pip3 install django
django createproject myproject
cd myproject
git clone https://bitbucket.org/abando/esupa.git
```
* Add `esupa` to your project's settings and URLs.

### Contribution guidelines ###

* I will take non-breaking pull requests.
* You can be added to the project after a successful pull request if you so desire.

### Authors ###

At the moment it's all by @ekevoo, but heavily based on plenty of discussions and advice from @whiteraccoon, who really helped mature the ideas while working hard at the PHP predecessor of this.