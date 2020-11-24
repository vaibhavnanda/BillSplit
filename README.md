# BillSplit
BillSplit is a web application developed using Flask.  
The main purpose of this project was to get familiar with Flask.  
BillSplit is an application similar to splitwise.  

# Working
BillSplit uses Google O-Auth for loging in users and maintaining the sessions. Each user is provided with some functionalities which are discussed below:

# Home Page
At the home page you're provided with some options you can choose from. The home page also displays your profile picture and the total amount your friends owe you as well as the amount you owe them.

# Adding friends
Each user can add new friends to their list. A user can only be added if the person is already registered with the app. If there's a person who owes you money for an event or a person you have to pay for an event, then they are automatically added to your friends list.  
The friends module also shows how much your friend owes you and how much you owe them.

# Split
Each user can add a new event in which the user can select the friends involved in that transaction, the total amount spent, every involved person's share, and how much they owe.  
The user is provided with 2 options, either to split the money equally amongst the group or to split the money manually. By splitting the money manually, we can decide how much a particular person owes for the event.

# Events
In this module you can retrieve information about the past events you were involved in. The information of the events like the date of the event, transactions made and people involved can be viewed here.  
While viewing the information of a particular event, you also get an option from where you can select whether a friend has paid you the money they owed you, or if you've paid the money you owed them.

# Notifications
Each user is notified when they're added to an event. Both the users are notified when a transaction involving them is processed. The notifications are sorted on the basis of date and time.

# User Info
We can retrieve information like name, profile picture and email of the users by clicking on their profile pictures/name. Dynamic URL is used to redirect you to the user info page. This functionality is useful in cases when 2 or more users have the same profile picture and name. Using this functionality we can be sure to add the person we want to, and not someone else.
