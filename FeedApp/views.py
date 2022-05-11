from django.shortcuts import render, redirect
from .forms import PostForm,ProfileForm, RelationshipForm
from .models import Post, Comment, Like, Profile, Relationship
from datetime import datetime, date

from django.contrib.auth.decorators import login_required
from django.http import Http404


# Create your views here.

# When a URL request matches the pattern we just defined, 
# Django looks for a function called index() in the views.py file. 

def index(request):
    """The home page for Learning Log."""
    return render(request, 'FeedApp/index.html')


# login_required is a decorator, verification
@login_required
def profile(request):
    profile = Profile.objects.filter(user=request.user)
# normally, get would be used to pull a single user. However, filter is used in this instance because exists() does not work with get for some reason.
    if not profile.exists():
        Profile.objects.create(user=request.user)
# if the user does not have a profile already, the Boolean above triggers line 26, which creates a user for them. At this point, we know the user now has a profile,
# so the get method is called.
    profile = Profile.objects.get(user=request.user)

    if request.method != 'POST':
        form = ProfileForm(instance=profile)
    else:
        form = ProfileForm(instance=profile,data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('FeedApp:profile')
    context = {'form':form}
    return render(request, 'FeedApp/profile.html',context)

@login_required
def myfeed(request):
# we are creating two empty lists that will store the numbers of likes and comments for the posts for the feed of a particular user. First, we create the post object, which pulls from
# the Post class in the models.py file. Saved posts are filtered by username and ordered by date posted in descending order, so newer likes and comments come to the
# forefront.
    comment_count_list = []
    like_count_list = []
    posts = Post.objects.filter(username=request.user).order_by('-date_posted')
    for p in posts:
# here we pull the comment and like counts for each post in the posts object. These values are appended to the lists we created above.
        c_count = Comment.objects.filter(post=p).count()
        l_count = Like.objects.filter(post=p).count()
        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    zipped_list = zip(posts,comment_count_list,like_count_list)
    context = {'posts':posts,'zipped_list':zipped_list}
    return render(request,'FeedApp/myfeed.html',context)


@login_required
def new_post(request):
    if request.method != 'POST':
        form = PostForm()
    else:
        form = PostForm(request.POST,request.FILES)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.username = request.user
            new_post.save()
            return redirect('FeedApp:myfeed')
    context = {'form':form}
    return render(request,'FeedApp/new_post.html',context)

@login_required
def friendsfeed(request):
    comment_count_list=[]
    like_count_list=[]
    friends = Profile.objects.filter(user=request.user).values('friends')
    posts = Post.objects.filter(username__in=friends).order_by('-date_added')
    for p in posts:
        c_count=Comment.objects.filter(post=p).count()
        l_count=Like.objects.filter(post=p).count()
        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    zipped_list = zip(posts,comment_count_list,like_count_list)

    if request.method =='POST' and request.POST.get('like'):
        post_to_like = request.POST.get('like')
        like_already_exists = Like.objects.filter(post_id=post_to_like,username=request.user)
        if not like_already_exists.exists():
            Like.objects.create(post_id=post_to_like,username=request.user)
            return redirect('FeedApp:FriendsFeed')
    context={'posts':posts,'zipped_list':zipped_list}
    return render(request,'FeedApp/friendsfeed.html',context)

@login_required
def comments(request,post_id):
    if request.method == 'POST' and request.POST.get('btn1'):
# btn1 is the button we will create in the html file
        comment = request.POST.get('comment')
        Comment.objects.create(post_id=post_id,username=request.user,text=comment,date_added=date.today())
    
    comments = Comment.objects.filter(post=post_id)
    post = Post.objects.get(id=post_id)
    context = {'post':post,'comments':comments}

    return render(request, 'FeedApp/comments.html',context)


@login_required
def friends(request):
    admin_profile = Profile.objects.get(user='admin')
    #admin_profile pulls the first user of the app, which is the admin
    user_profile = Profile.objects.get(user=request.user)
    user_friends = user_profile.friends.all()
    #user profile is an instance of the Profile class in models.py
    user_friends_profiles = Profile.objects.filter(user__in=user_friends)
    #friends is an attribute of Profile and user_friends_profiles is calling all the friends as a list
    
    user_relationships = Relationship.objects.filter(sender=user_profile)
    request_sent_profiles = user_relationships.values('receiver')
    #sender is an attribute of the Relationship class. It's a Django model.
    #Here, we call all requests where the sender is the user. This comes from
    #the request.user field
    #Because we have no algorithm in the system that displays recommended profiles,
    #we show the user every other profile as recommended for being added.
    all_profiles = Profile.objects.exclude(user=request.user).exclude(id__in=user_friends_profiles).exclude(id__in=request_sent_profiles)
    #The excludes are used to remove three groups of users from the recommended list.
    #First, the user account itself.
    #Second, the list of all users that the user is currently friends with.
    #Third, the list of all users that the user has already sent requests to.
    request_received_profiles = Relationship.objects.filter(receiver=user_profile,status='sent')

    if not user_relationships.exists():
        Relationship.objects.create(sender=user_profile,receiver=admin_profile,status='sent')
        #relationship = Relationship.objects.filter(sender=user_profile,status='sent')

    # check to see which submit button was pressed (either accepting request or sending request)
    if request.method == 'POST' and request.POST.get('send_requests'):
        receivers = request.POST.getlist('send_requests')
        # check boxes so we need a list
        for receiver in receivers:
            receiver_profile = Profile.objects.get(id=receiver)
            Relationship.objects.create(sender=user_profile,receiver=receiver_profile,status='sent')
        return redirect('FeedApp:friends')
    # this is to process all receive requests
    if request.method == 'POST' and request.POST.get('receive_requests'):
        senders = request.POST.getlist('receive_requests')
        for sender in senders:
            Relationship.objects.filter(id=sender).update(status='accepted')

            #create a relationship object to access the senders' user id
            relationship_obj = Relationship.objects.get(id=sender)
            user_profile.friends.add(relationship_obj.sender.user)
            #add the user to the friends list of the sender's profile
            relationship_obj.friends.add(request.user)
    context = {'user_friends_profiles':user_friends_profiles,'user_relationships':user_relationships,
                'all_profiles':all_profiles,'request_received_profiles':request_received_profiles}
    return render(request,'FeedApp/friends.html',context)                

