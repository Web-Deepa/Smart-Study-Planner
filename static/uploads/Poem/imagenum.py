#numpy for image 
"""
import numpy as np
print(np.__version__) 
m=np.array([1,2])
print(m.ndim)
m.shape,m.size
np.arrange(10)
np.eye(5) #identity matrix
print(m.reshape(2,2))

np.min(a)
np.sort(a)
np.sort(a[::-1])
"""

import numpy as np
import random
a=np.array([1,2,4,5,8,9,2,43,90,76,58])
 
#1.Print all even numbers 
"""
print("even numbers:")
for n in a:
 if n%2==0:
  print(n)

#2.find sum of all elements in  array
sum=0
print("sum:")
for n in  a:
    sum+=n
    print(sum)
    
#3.find maximum and minimum value
print("Maximum:",np.max(a))
print("Minimum:",np.min(a))

#4.count how many numbers are greater than  
count=0
print("numbers greater than 10:")
for n in a:
    if n>10:
        print(n)
    

#5.create a new array where each element is multiplied by 2
a_mul=np.array=[]
for n in a:
    a_mul.append(n*2)
print(a_mul)    

#6.replace all values less than 10 with 10 (wihtout using loops)
a_rep=[]
for n in a:
    if n<10:
        a_rep.append(10)
    else:
        a_rep.append(n)
print("Replaced array:",a_rep)
#7.reverse the array
a_rev = []
for i in range(len(a) - 1, -1, -1):
  a_rev.append(a[i])
print(a_rev)


#1.create array of 10 num
arr=np.array([1,2,3,5,4,6,7,8,9,0])
print("10 elements array:",arr)
#2.find 1st and last element
first=np.arr[0]
last=np.arr[-1]
print("first element:",first)
print("last element:",last)
#3.find maximum,4.
print("Minuimum value:",np.min(arr))
print("Maximum value:",np.max(arr))

#5.average
avg=np.mean(arr)
print("average:",avg)
#6.3*3 using reshape
arr_reshape=arr.reshape(3,3)
print("Reshaped array:",arr_reshape)
#7.add two array
arr2=np.array([4,5,6,7,8,9,0,12,34,60])
#8.Multiply by 5
arr_mul=[]
for n in arr:
    arr_mul.append(n*5)
print("multiplied by 5 array:",arr_mul)    
    

#9. intergers betwen 1 to 10 
ran_arr=[]
for i in range(10):
    n=random.randint(1,10)
    ran_arr.append(n)
print("random numbers array:",ran_arr)    

#10.sort in ascending order
print("Ascending aorder:",np.sort(arr))

"""
#1.Create 1D array containing numbers 1 to 10 print its size,shape and data type.Then create a 3x3 identity matrix and 4x4 array of random numbers between 1 and 100

"""b=np.array([1,4,3,2,5,7,6,8,9,10])
print("Array:",b)
print("Array shape:",b.shape)
print("Array size:",b.size)
print("Data type:",a.dtype)
i=np.eye(3)
print("identity matrix:",i)

c=[]
for i in range(4):
    row=[]
    for j in range(4):
      n=random.randint(1,10)
      row.append(n)
    c.append(row)
print("matrix:",c)"""

#2.Given arr=np.array([10,20,30,40,50,60]),extract the first three elements and last two elements seperately.Then given a 5x5 array of random integers,extract the second row and third column

arr=np.array([10,20,30,40,50,60])
print("array:",arr)
print("first 3 elements;")
for i in range(3):
    print(i)

print("Last two elements:")
print(arr[-2:]) 
