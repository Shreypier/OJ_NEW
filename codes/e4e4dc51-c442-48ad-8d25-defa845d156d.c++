#include <iostream>
using namespace std;
int main() {
     int t;
     cin>>t;
     while(t--)
     {
         int n;
         cin>>n;
         int count=0;
         while(n!=0)
         {
             count++;
             n=n/10;
         }
         cout<<count+1<<"\n";//checking
     }
    return 0;
}