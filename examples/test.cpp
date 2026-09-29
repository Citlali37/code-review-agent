#include<bits/stdc++.h>
using namespace std;
#define int long long
#define endl "\n"
void solve() {
    vector<int>a(6),b(7);
    b[0]=1;
    for (int i=0;i<6;++i) {
        cin>>a[i];
        b[i+1]=a[i]+1;
    }
    int k;cin>>k;
    vector<int>res;
    int sum=0;
    auto check=[&]() {
        int cnt=0;
        sum=0;
        for (int i=0;i<6;++i) {
            for (int j=0;j<6;++j) {
                if (res[i]>a[j])cnt++;
            }
            sum+=res[i];
        }
        // cout<<cnt<<endl;
        return (cnt>=19&&sum<=k);
    };
    vector<int>RES;
    int flag=0,SUM=0;
    function<void(int)>dfs=[&](int p) {
        if (flag)return;
        if (p==6) {
            if (check()) {flag=1;RES=res;SUM=sum;}
            return;
        }
        for (int i=0;i<7;++i) {
            res.push_back(b[i]);
            dfs(p+1);
            res.pop_back();
        }
    };
    dfs(0);
    if (flag==0) cout<<"NO"<<endl;
    else {
        cout<<"YES"<<endl;
        RES[0]+=k-SUM;
        for (int i=0;i<6;++i)cout<<RES[i]<<" \n"[i==5];
    }

}
signed main() {
// #ifndef ONLINE_JUDGE
//     freopen("in.txt", "r", stdin);
//     freopen("out.txt", "w", stdout);
// #endif
    ios::sync_with_stdio(0),cin.tie(0),cout.tie(0);
    int t=1;
    // cin>>t;
    while(t--)solve();
}