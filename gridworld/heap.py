"""Part 2: implement a binary min-heap. YOU EDIT THIS FILE.

Store (priority, item) pairs in an array. Compare priorities, not items.
For index i, the children are 2*i + 1 and 2*i + 2, and the parent is
(i - 1) // 2. Each parent's priority must be at most its children's priorities.

Use your own heap; ready-made priority queues are not allowed. The autograder
checks correctness and the number of priority comparisons.
"""
from __future__ import annotations


class BinaryHeap:
    """A min-heap of ``(priority, item)`` pairs.

    TODO (Part 2a). Implement :meth:`push`, :meth:`pop` and :meth:`__len__`,
    keeping the pairs in ``self.data`` with the smallest priority at index 0.

    The autograder reads ``self.data`` directly and checks the invariant after
    every operation on long random sequences. It also counts comparisons and
    expects the amortised count to stay within a small multiple of ``log2 n``,
    so a re-sorted list is correct but will not fit the budget.
    """

    __slots__ = ("data",)

    def __init__(self):
        #: the heap array: a list of ``(priority, item)`` pairs
        self.data: list[tuple] = []

    def __len__(self) -> int:
        #"""TODO (Part 2a).  How many pairs are in the heap."""
        return len(self.data)

    def __bool__(self) -> bool:
        return len(self) > 0

    def push(self, priority, item) -> None:
        """Insert one pair.

        TODO (Part 2a). Append, then sift up: while it is smaller than its
        parent, swap the two.
        """

        #the heap stores pairs (priority,items)
        #add the new pair to the end of the list
        self.data.append((priority,item))

        #every parents priority must be less than or equal to the childs priority
        # i is the index of the new item since it starts at 0 
        i = len(self.data)-1

        # we keep moving the item up as long as it isnt the root
        while i>0: 
            p = (i-1)//2 #parent calculation 

            #using [0] directly gives us the priority
            #this conditional checks if the childs priority is bigger than the parents 
            #which would mean the heap is correct and we stop
            if self.data[i][0] >= self.data[p][0]: 
                break 

            #if the child is smaller we swap
            self.data[i], self.data[p] = (
                self.data[p], self.data[i]
            )

            #move index to compare at new position
            i = p
        

    def pop(self):

        #pop needs to save the root, remove the last item, put the last item as the root
        #move it downward to make the heap right again, and return the item from the original root

        # this saves the root
        rootitem = self.data[0][1]

        #remove the last element 
        final = self.data.pop()

    #ensure the list is not empty in case there was only one item in the list before the pop
        if self.data: 

            #make the last item the root 
            self.data[0]= final

            i=0
            #using x to keep track of numner of items in the heap
            x = len(self.data)

            #need to just keep chekcing until we decide we are finished 
            #either we reached the bottom, or the heap is correct 
            while True: 
                l = (2*i)+1 #calculation for left child
                r = (2*i)+2 #calculation for right child 

                #means no left child exists
                if l>=x: 
                    break

                #assuming left has the smallest priority
                smallest = l 

                #now compare the left and right
                #first does right exists and is its priority less than the lefts
                if(r<x and self.data[r][0]<self.data[l][0]):
                    smallest = r 

                #check if already at the right index
                if self.data[i][0]<=self.data[smallest][0]: 
                    break 

                #if condition above is false we swap
                self.data[i],self.data[smallest] = (
                    self.data[smallest], 
                    self.data[i])

                #move down 
                i = smallest

        # when done we return the original root
        return rootitem

       
        

   

        