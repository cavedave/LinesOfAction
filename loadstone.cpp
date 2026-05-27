/*
  Name:        LoAdstone.cpp
  Version:     2.0
  Date:        28 May 2005
  Description: a Lines-of-Action player
  Copyright:   ask the author
  Author:      Claude Chaunier
  Contact:     c l a u c h a u  w a n a d o o  f r

  Available on: http://clauchau.free.fr
  Discussed on: http://www.linesofaction.com/forum/viewtopic.php?t=22
  
  Compile with: gcc 3.2.3 and Fast Light ToolKit 1.1.2

  Best viewed with tabs worth two spaces

  Try and change:
    - the SQUARE and STONE WIDTHS = eg. (5,4), (15,12), (31,24), (45,36), ...

*/

int N; // the board starts with NxN squares, with 5 <= N <= MAX_N
int INITIAL_SETUP; // 0,1,2=sparse; 3=standard,4,5; 6,7,8=dense

const int SQUARE_WIDTH = 31; // pixel width and height of every board square
const int  STONE_WIDTH = 24; // pixel width and height of every stone

const int SQUARE_COLOR[2][3] = {{255,204,153},{215,164,113}}; // [remember?][RGB]
const int  STONE_COLOR[2][3] = {{(226+100)/2, (107+54)/2, (3+55)/2}, {255, 240, 227}}; // [player   ][RGB]

const double SQUARE_THICKNESS[2] = {-.2,.4}; // down and up
const double  STONE_THICKNESS[2] = { .5,.5 };
const double DIRECT_LIGHT[2][2] = {{.8,.8},{.8,.9}}; // [up?][highlighted?]
#include <math.h>
const double alpha = M_PI*3/4; // from where the light comes (eg. North West)
const double theta = M_PI/3;   // how high it is (PI/2 = noon)
const double delta = M_PI/64;  // small angle between sub-pieces of light
const double AMBIENT = (1. - sin(theta)*DIRECT_LIGHT[0][0]);
const double beta = M_PI/2; // how high the observator is
const double cos_5delta = cos(delta*5);

const int MAX_N = 16; // constrained to N <= MAX_N <= 16
const int MAX_NS = 64; // every player's maximum Number of Stones, <= 64

// -------------------------------------------------------------------

const int INFI = 0x7fffffffL;
const int FIRST_PLAYER = 0;
const int SECOND_PLAYER = 1;

inline int sqr(const int x) { return x*x; }
inline double sqr(const double x) { return x*x; }
inline int min(const int a, const int b) { return (a<b)? a: b; };
inline int max(const int a, const int b) { return (a>b)? a: b; };

// ------------------------------------------------------------------------
// random number generator adapted from Donald Knuth's Standford GraphBase (1993)

#define ulong unsigned long

ulong A[55];	// pseudo-random values (from 0 to 2^32-1, unlike Knuth's)
int iA;			// index of the last value in A[] that was used
ulong twirl;
ulong g = 1;	// growing pseudo-root modulo 2^32;

ulong flip_cycle()	// compute 55 more pseudo-random numbers
{	ulong *ii, *jj;

	for(ii = &A[0], jj = &A[31]; jj<=&A[54]; ++ii, ++jj) {
		if(twirl&1) twirl = 0x80000000UL+(twirl>>1); else twirl >>= 1;
		*ii = (*ii-twirl)*0x17196903UL-(*jj*0x19742103UL)^(g *= 0x21011975UL);
	}
	for(jj = &A[0]; ii<=&A[54]; ++ii, ++jj) {
		if(twirl&1) twirl = 0x80000000UL+(twirl>>1); else twirl >>= 1;
		*ii = (*ii-twirl)*0x17196903UL-(*jj*0x19742103UL)^(g *= 0x21011975UL);
	}
	// Knuth only did the fast *ii -= *jj and it was a catastroph for my hashing
	// function because my hash numbers are sums of random numbers and they would
	// often get unexpectedly equal.

	return A[iA = 54];
}

void rand_init(ulong seed)
{	ulong prev, next = 0x12011969UL; // Knuth set next=1 here instead

	A[0] = prev = twirl = seed^0xa5a5a5a5;	// not what Knuth did either, but as good
	for(ulong i = 21; i; i = (i+21)%55) {
		A[i] = next;
		if(twirl&1) twirl = 0x80000000UL+(twirl>>1); else twirl >>= 1;
		next = prev*0x17196903UL-next*0x19742103UL-twirl*0x21011975UL;
		// and here Knuth only did  next = prev-next-seed;
		prev = A[i];
	}
	flip_cycle();	// get the array values "warmed up"
	flip_cycle();
	flip_cycle();
	flip_cycle();
	flip_cycle();
}

inline ulong rand_next()
{	return (--iA>=0)? A[iA]: flip_cycle();
}

// -------------------------------------------------------------------

const int DI[] = {-1,-1,  -1,0,+1,+1,+1,0,  -1,-1}; // differences for the row i
const int *DJ = DI+2; // differences for the col number j along the 8 dirs
const int DP[] = {-MAX_N-3,-MAX_N-2,-MAX_N-1,+1,MAX_N+3,MAX_N+2,MAX_N+1,-1};
/*
    0 1 2
    7 * 3
    6 5 4
*/

class Square {
protected:
  int content;
public:
  bool is_empty()    const { return content==0; };
  bool is_occupied() const { return content> 0; };
  bool is_inside()   const { return content>=0; };
  bool is_outside()  const { return content< 0; };

  void empty()                    { content = 0;           };
  void occupy(const int stone_id) { content = stone_id+MAX_NS; };
  void outside()                  { content = -1;          };

  int stone_id()      const { return content-MAX_NS; }
  int short_content() const { return content/MAX_NS; } // 0 if empty, player+1 otherwise
  int player()        const { return content/(MAX_NS*2); }
  int player_mask()   const { return content&(MAX_NS*3); }

  bool is_friendly_occupied(const int playerMask) const {
    return (content&(MAX_NS*3))==playerMask;
  }
  bool can_land_on(const Square *to) const {
    return (player_mask()&to->content)==0;
  }
};

inline int player_mask(const int stone_id) {
  return (stone_id+MAX_NS)&(MAX_NS*3);
}

// -------------------------------------------------------------------

int player; // 0 = first player, 1 = second player
Square square[MAX_N+2][MAX_N+2]; // the board [row][col]
/*

board[i][j] = EMPTY | stone id + MAX_NS | WALL

 X X X X X    X X
 X1,1. . .    . X
 X2,1. . .    . X
 X . .3,3.    . X
 X . .4,3.    . X

 X . . . .   N,NX
 X X X X X    X X

 
 0 1 2 X X    X X
1617 . . .    . X
32 .34 . .    . X
 X . .51 .    . X
 X . . .68    . X

 X . . . .  17N X
 X X X X X    X X
 
*/

const int MAX_LEN_1 = MAX_N;
const int MAX_LEN_2 = MAX_N*2-1;
const int MAX_LEN_01= MAX_N*3-2;

const int MAX_LEN_3 = MAX_LEN_1;
const int MAX_LEN_4 = MAX_LEN_2;
const int MAX_LEN_12= MAX_LEN_01;
const int MAX_LEN_23= MAX_LEN_01;
const int MAX_LEN_34= MAX_LEN_01;

#define len_1  (N)
#define len_2  (N*2-1)
#define len_01 (N*3-2)

//ulong hash_index_basis[16][16];
//ulong hash_clash_basis[16][16];
//ulong hash_index_key;
//ulong hash_clash_key;

int nb_of_stones[2];
int sumi[2], sumj[2], sumi2[2], sumj2[2];
int nb_of_avail_moves[2];
int nb_of_captu_moves[2];
int count_1[MAX_LEN_1], // j-1
    count_2[MAX_LEN_2], // i+j-2
    count_3[MAX_LEN_3], // i-1
    count_4[MAX_LEN_4]; // i-j+N-1
//  0 1 2
//  7 * 3
//  6 5 4
int projected_01[2][MAX_LEN_01], // 2j-i+N-2
/*
    3 5 7 9
    2 4 6 8
    1 3 5 7
    0 2 4 6
*/
    projected_1[2][MAX_LEN_1], // j-1
/*
    0 1 2 3
    0 1 2 3
    0 1 2 3
    0 1 2 3
*/
    projected_12[2][MAX_LEN_12], // i+2j-3
/*
    0 2 4 6
    1 3 5 7
    2 4 6 8
    3 5 7 9
*/
	projected_2[2][MAX_LEN_2], // i+j-2
/*
    0 1 2 3
    1 2 3 4
    2 3 4 5
    3 4 5 6  square +(i+j-N-1)*(MAX_N+2)+N+1
*/
	projected_23[2][MAX_LEN_23], // 2i+j-3
/*
    0 1 2 3
    2 3 4 5
    4 5 6 7
    6 7 8 9
*/
	projected_3[2][MAX_LEN_3], // i-1
/*
    0 0 0 0
    1 1 1 1
    2 2 2 2
    3 3 3 3
*/
    projected_34[2][MAX_LEN_34], // 2i-j+N-2
/*
    3 2 1 0
    5 4 3 2
    7 6 5 4
    9 8 7 6
*/
    projected_4[2][MAX_LEN_4]; // i-j+N-1
/*
    3 2 1 0
    4 3 2 1
    5 4 3 2
    6 5 4 3
*/
inline int coord_project_0 (const int i, const int j) { return i-j+N-1; }
inline int coord_project_1 (const int i, const int j) { return j-1; }
inline int coord_project_2 (const int i, const int j) { return i+j-2; }
inline int coord_project_3 (const int i, const int j) { return i-1; }
inline int coord_project_4 (const int i, const int j) { return i-j+N-1; }
inline int coord_project_5 (const int i, const int j) { return j-1; }
inline int coord_project_6 (const int i, const int j) { return i+j-2; }
inline int coord_project_7 (const int i, const int j) { return i-1; }
inline int coord_project_01(const int i, const int j) { return j*2-i+N-2; }
inline int coord_project_12(const int i, const int j) { return i+j*2-3; }
inline int coord_project_23(const int i, const int j) { return i*2+j-3; }
inline int coord_project_34(const int i, const int j) { return i*2-j+N-2; }


class Stone {
public:
	int row, col;
	bool is_on_board;
	int nb_avail_dirs;
	int nb_captu_dirs;
  int avail_dirs;	// 8 first bits showing the valid move directions
  int captu_dirs;	// 8 first bits showing the valid capturnig move directions
//  0 1 2
//  7 * 3
//  6 5 4
  int root; // index of one stone, the same in the connected component
  int component_id; // identifies too the connected component
  int component_size; // defined on the root stone of every component

  Square *squarep() const { return &square[row][col]; }
};

Stone stone[64*2];
int free_stone_id[2]; // index in stone[] for the next stone to be born at setup

void board_new() // N must be properly set to the size board before
{
    // empty the board and mark the outer walls
	for(int j=0; j<=N+1; ++j) {
		square[0][j].outside();
    square[N+1][j].outside();
  }
	for(int i=1; i<=N; ++i) {
		square[i][0].outside();
    square[i][N+1].outside();
		for(int j=1; j<=N; ++j)
			square[i][j].empty();
	}

	nb_of_stones[0] = nb_of_stones[1] = 0; // no stones on board
	free_stone_id[0] = 0; // means the first player list of stones is empty
	free_stone_id[1] = MAX_NS; // means the 2nd player list of stones is empty
	
	for(int ij=0; ij<N; ++ij) // empty the horizontal and vertical projected
    count_1[ij] = count_3[ij] =
		projected_1[0][ij] = projected_1[1][ij] =
		projected_3[0][ij] = projected_3[1][ij] = 0;
	for(int ij=0; ij<N*2-1; ++ij) // empty the diagonal projected
    count_2[ij] = count_4[ij] =
		projected_2[0][ij] = projected_2[1][ij] =
		projected_4[0][ij] = projected_4[1][ij] = 0;
	for(int ij=0; ij<N*3-2; ++ij) // empty the 50%-slopy projected
		projected_01[0][ij] = projected_01[1][ij] =
		projected_12[0][ij] = projected_12[1][ij] =
		projected_23[0][ij] = projected_23[1][ij] =
		projected_34[0][ij] = projected_34[1][ij] = 0;

	sumi[0] = sumi2[0] = sumj[0] = sumj2[0] =
	sumi[1] = sumi2[1] = sumj[1] = sumj2[1] = 0;
	
	nb_of_avail_moves[0] = nb_of_avail_moves[1] =
  nb_of_captu_moves[0] = nb_of_captu_moves[1] = 0;
}

inline void projected_inc(const int i, const int j, const int player) {
  ++count_1[coord_project_1(i,j)];
	++count_2[coord_project_2(i,j)];
	++count_3[coord_project_3(i,j)];
  ++count_4[coord_project_4(i,j)];
  ++projected_01[player][coord_project_01(i,j)];
  ++projected_1 [player][coord_project_1 (i,j)];
  ++projected_12[player][coord_project_12(i,j)];
	++projected_2 [player][coord_project_2 (i,j)];
	++projected_23[player][coord_project_23(i,j)];
	++projected_3 [player][coord_project_3 (i,j)];
  ++projected_34[player][coord_project_34(i,j)];
  ++projected_4 [player][coord_project_4 (i,j)];
}

inline void projected_dec(const int i, const int j, const int player) {
  --count_1[coord_project_1(i,j)];
	--count_2[coord_project_2(i,j)];
	--count_3[coord_project_3(i,j)];
  --count_4[coord_project_4(i,j)];
  --projected_01[player][coord_project_01(i,j)];
  --projected_1 [player][coord_project_1 (i,j)];
  --projected_12[player][coord_project_12(i,j)];
	--projected_2 [player][coord_project_2 (i,j)];
	--projected_23[player][coord_project_23(i,j)];
	--projected_3 [player][coord_project_3 (i,j)];
  --projected_34[player][coord_project_34(i,j)];
  --projected_4 [player][coord_project_4 (i,j)];
}

// the 2 next functions assume that only one stone has been added or taken off
void update_avail_dirs_along(Square *edge, const int dir, int ns) {
  if(ns==0) return;
  const int op_dir = (dir+4)%8; // opposite direction
  const int dir_mask = 1<<dir;
  const int dir_antimask = (-1)^dir_mask;
  const int op_dir_mask = 1<<op_dir;
  const int op_dir_antimask = (-1)^op_dir_mask;
  const int dp = DP[dir];
  int between[2] = {0,0}; // nb of each player's stones between edge and to
  Square *to = edge;
  while(--ns) {
    if((to += dp)->is_occupied())
      ++between[to->player()];
  }
  to += dp;
  do {
    if(to->is_occupied()) {
      if(between[to->player()^1]==0 && to->can_land_on(edge)) {
        if((stone[to->stone_id()].avail_dirs & op_dir_mask)==0) {
          ++stone[to->stone_id()].nb_avail_dirs;
          ++nb_of_avail_moves[to->player()];
          stone[to->stone_id()].avail_dirs |= op_dir_mask;
          if(edge->is_occupied()) {
            ++stone[to->stone_id()].nb_captu_dirs;
            ++nb_of_captu_moves[to->player()];
            stone[to->stone_id()].captu_dirs |= op_dir_mask;
          }
        }
      }
      else {
        if((stone[to->stone_id()].avail_dirs & op_dir_mask)) {
          --stone[to->stone_id()].nb_avail_dirs;
          --nb_of_avail_moves[to->player()];
          stone[to->stone_id()].avail_dirs &= op_dir_antimask;
          if(stone[to->stone_id()].captu_dirs & op_dir_mask) {
            --stone[to->stone_id()].nb_captu_dirs;
            --nb_of_captu_moves[to->player()];
            stone[to->stone_id()].captu_dirs &= op_dir_antimask;
          }
        }
      }
      ++between[to->player()];
    }
    to += dp;
    if((edge += dp)->is_occupied()) {
      --between[edge->player()];
      if(between[edge->player()^1]==0 && edge->can_land_on(to)) {
        if((stone[edge->stone_id()].avail_dirs & dir_mask)==0) {
          ++stone[edge->stone_id()].nb_avail_dirs;
          ++nb_of_avail_moves[edge->player()];
          stone[edge->stone_id()].avail_dirs |= dir_mask;
          if(to->is_occupied()) {
            ++stone[edge->stone_id()].nb_captu_dirs;
            ++nb_of_captu_moves[edge->player()];
            stone[edge->stone_id()].captu_dirs |= dir_mask;
          }
        }
      }
      else {
        if((stone[edge->stone_id()].avail_dirs & dir_mask)) {
          --stone[edge->stone_id()].nb_avail_dirs;
          --nb_of_avail_moves[edge->player()];
          stone[edge->stone_id()].avail_dirs &= dir_antimask;
          if(stone[edge->stone_id()].captu_dirs & dir_mask) {
            --stone[edge->stone_id()].nb_captu_dirs;
            --nb_of_captu_moves[edge->player()];
            stone[edge->stone_id()].captu_dirs &= dir_antimask;
          }
        }
      }
    }
  } while(to->is_inside());
}

void update_avail_dirs(const int i, const int j) {
  update_avail_dirs_along( &square[i][0],
    3, count_3[coord_project_3(i,j)] );
  update_avail_dirs_along( &square[0][0] + max( j-i , (i-j)*(MAX_N+2) ),
    4, count_4[coord_project_4(i,j)] );
  update_avail_dirs_along( &square[0][j],
    5, count_1[coord_project_1(i,j)] );
  update_avail_dirs_along( &square[0][0] + max( i+j , (i+j-N-1)*(MAX_N+2)+N+1 ),
    6, count_2[coord_project_2(i,j)] );
}

//--------------------------------------------

/*

0 1 2
7   3
6 5 4

. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
. . .   . . .   . . .   . . .   . . .   . . .   . . .   . . .
-0000100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   x   .   x   .   x   .   x   .   x   .   x   .   x   .   x
. . .   . . .   . . .   . . .   . . .   . . .   . . .   . . .
01000100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
. . x   . . x   . . x   . . x   . . x   . . x   . . x   . . x
01111211
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   x   .   x   .   x   .   x   .   x   .   x   .   x   .   x
. . x   . . x   . . x   . . x   . . x   . . x   . . x   . . x
01000100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
. x .   . x .   . x .   . x .   . x .   . x .   . x .   . x .
01111211
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   x   .   x   .   x   .   x   .   x   .   x   .   x   .   x
. x .   . x .   . x .   . x .   . x .   . x .   . x .   . x .
01000100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
. x x   . x x   . x x   . x x   . x x   . x x   . x x   . x x
01111211
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   x   .   x   .   x   .   x   .   x   .   x   .   x   .   x
. x x   . x x   . x x   . x x   . x x   . x x   . x x   . x x
01000100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
x . .   x . .   x . .   x . .   x . .   x . .   x . .   x . .
01111211
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   x   .   x   .   x   .   x   .   x   .   x   .   x   .   x
x . .   x . .   x . .   x . .   x . .   x . .   x . .   x . .
12111211
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
x . x   x . x   x . x   x . x   x . x   x . x   x . x   x . x
12222322
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   x   .   x   .   x   .   x   .   x   .   x   .   x   .   x
x . x   x . x   x . x   x . x   x . x   x . x   x . x   x . x
12111211
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
x x .   x x .   x x .   x x .   x x .   x x .   x x .   x x .
01111211
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   x   .   x   .   x   .   x   .   x   .   x   .   x   .   x
x x .   x x .   x x .   x x .   x x .   x x .   x x .   x x .
01000100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
x x x   x x x   x x x   x x x   x x x   x x x   x x x   x x x
01111211
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
.   x   .   x   .   x   .   x   .   x   .   x   .   x   .   x
x x x   x x x   x x x   x x x   x x x   x x x   x x x   x x x
01000100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   .   x   .   x   .   x   .   x   .   x   .   x   .   x   .
. . .   . . .   . . .   . . .   . . .   . . .   . . .   . . .
00001100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   x   x   x   x   x   x   x   x   x   x   x   x   x   x   x
. . .   . . .   . . .   . . .   . . .   . . .   . . .   . . .
11001100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   .   x   .   x   .   x   .   x   .   x   .   x   .   x   .
. . x   . . x   . . x   . . x   . . x   . . x   . . x   . . x
11112211
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   x   x   x   x   x   x   x   x   x   x   x   x   x   x   x
. . x   . . x   . . x   . . x   . . x   . . x   . . x   . . x
11001100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   .   x   .   x   .   x   .   x   .   x   .   x   .   x   .
. x .   . x .   . x .   . x .   . x .   . x .   . x .   . x .
00001100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   x   x   x   x   x   x   x   x   x   x   x   x   x   x   x
. x .   . x .   . x .   . x .   . x .   . x .   . x .   . x .
00000000
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   .   x   .   x   .   x   .   x   .   x   .   x   .   x   .
. x x   . x x   . x x   . x x   . x x   . x x   . x x   . x x
00001100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   x   x   x   x   x   x   x   x   x   x   x   x   x   x   x
. x x   . x x   . x x   . x x   . x x   . x x   . x x   . x x
00000000
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   .   x   .   x   .   x   .   x   .   x   .   x   .   x   .
x . .   x . .   x . .   x . .   x . .   x . .   x . .   x . .
00001100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   x   x   x   x   x   x   x   x   x   x   x   x   x   x   x
x . .   x . .   x . .   x . .   x . .   x . .   x . .   x . .
11001100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   .   x   .   x   .   x   .   x   .   x   .   x   .   x   .
x . x   x . x   x . x   x . x   x . x   x . x   x . x   x . x
11112211
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   x   x   x   x   x   x   x   x   x   x   x   x   x   x   x
x . x   x . x   x . x   x . x   x . x   x . x   x . x   x . x
11001100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   .   x   .   x   .   x   .   x   .   x   .   x   .   x   .
x x .   x x .   x x .   x x .   x x .   x x .   x x .   x x .
00001100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   x   x   x   x   x   x   x   x   x   x   x   x   x   x   x
x x .   x x .   x x .   x x .   x x .   x x .   x x .   x x .
00000000
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   .   x   .   x   .   x   .   x   .   x   .   x   .   x   .
x x x   x x x   x x x   x x x   x x x   x x x   x x x   x x x
00001100
. . .   x . .   . x .   x x .   . . x   x . x   . x x   x x x
x   x   x   x   x   x   x   x   x   x   x   x   x   x   x   x
x x x   x x x   x x x   x x x   x x x   x x x   x x x   x x x
00000000

*/

const int nb_of_mergings[256] =
//0 1 2 3 4 5 6 7 8 9 A B C D E F
{
 -1,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0, // 00
  0,1,1,1,1,2,1,1,0,1,0,0,0,1,0,0, // 10
  0,1,1,1,1,2,1,1,0,1,0,0,0,1,0,0, // 20
  0,1,1,1,1,2,1,1,0,1,0,0,0,1,0,0, // 30
  0,1,1,1,1,2,1,1,1,2,1,1,1,2,1,1, // 40
  1,2,2,2,2,3,2,2,1,2,1,1,1,2,1,1, // 50
  0,1,1,1,1,2,1,1,0,1,0,0,0,1,0,0, // 60
  0,1,1,1,1,2,1,1,0,1,0,0,0,1,0,0, // 70
  0,0,0,0,1,1,0,0,1,1,0,0,1,1,0,0, // 80
  1,1,1,1,2,2,1,1,1,1,0,0,1,1,0,0, // 90
  0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0, // A0
  0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0, // B0
  0,0,0,0,1,1,0,0,1,1,0,0,1,1,0,0, // C0
  1,1,1,1,2,2,1,1,1,1,0,0,1,1,0,0, // D0
  0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0, // E0
  0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0  // F0
};

int new_component_id = 0;
int nb_of_components[2]; // connecting friendly stones

#include <algorithm>
#include <vector>
#include <queue>

typedef std::queue<int> Stone_pool;

Stone_pool stone_pool;

void join(const int initial_root, const int target_root)
{ const int playerMask = player_mask(initial_root);
  const int target_id = stone[target_root].component_id;

  stone_pool.push(initial_root);
  do {
    const int s = stone_pool.front();
    const Square *to = stone[s].squarep();
    
    stone[s].root = target_root;
    stone[s].component_id = target_id;
    ++stone[target_root].component_size;
    stone_pool.pop();
    
    for(int dir=7; dir>=0; --dir) {
      const Square *neighbour_square = to+DP[dir];

      if(neighbour_square->is_friendly_occupied(playerMask)) {
        const int neighbour_stone = neighbour_square->stone_id();
        
        if(stone[neighbour_stone].root == initial_root) {
          stone_pool.push(neighbour_stone);
        }
      }
    }
  }while(!stone_pool.empty());
}

void square_occupy(const int i, const int j, const int s) // s is the stone_id
// Warning: the square is assumed empty
{
  Square * const to = &square[i][j];
  
	to->occupy(s);
	stone[s].row = i;
	stone[s].col = j;

  const int player = s/MAX_NS;

	projected_inc(i,j,player);
	sumi[player] += i;
	sumj[player] += j;
	sumi2[player] += sqr(i);
	sumj2[player] += sqr(j);
	//hash_index_key += hash_index_basis[i-1][j-1]*(player+1);
	//hash_clash_key += hash_clash_basis[i-1][j-1]*(player+1);

  stone[s].root = s;
  stone[s].component_id = ++new_component_id;
  stone[s].component_size = 1;
  ++nb_of_components[player];
  
  const int playerMask = player_mask(s);
  
  for(int dir=7; dir>=0; --dir) {
    const Square *neighbour = to+DP[dir];
    
    if(neighbour->is_friendly_occupied(playerMask)){
      const int neighbour_stone = neighbour->stone_id();
      const int neighbour_root = stone[neighbour_stone].root;

      if(neighbour_root != stone[s].root) {
        --nb_of_components[player];
        if(stone[s].root == s) {
          // Stone s is joining a fisrt connected component
          stone[s].root = neighbour_root;
          stone[s].component_id = stone[neighbour_stone].component_id;
          ++stone[neighbour_root].component_size;
        } else {
          // Stone s is joining anorther component as well
          if(stone[neighbour_root].component_size >= stone[s].component_size)
            join(neighbour_root, stone[s].root);
          else
            join(stone[s].root, neighbour_root);
        }
      }
      if(dir&1) --dir;
      --dir;
    }
  }
}

void rooting_inventory(const int initial_stone)
{ const int playerMask = player_mask(initial_stone);

  ++new_component_id;
  stone[initial_stone].component_size = 0;
  stone_pool.push(initial_stone);
  do {
    const int s = stone_pool.front();
    const Square *to = stone[s].squarep();

    stone[s].root = initial_stone;
    stone[s].component_id = new_component_id;
    ++stone[initial_stone].component_size;
    stone_pool.pop();

    for(int dir=7; dir>=0; --dir) {
      const Square *neighbour_square = to+DP[dir];

      if(neighbour_square->is_friendly_occupied(playerMask)) {
        const int neighbour_stone = neighbour_square->stone_id();

        if(stone[neighbour_stone].component_id != new_component_id) {
          stone_pool.push(neighbour_stone);
        }
      }
    }
  }while(!stone_pool.empty());
}

void square_empty(const int i, const int j, const int s) // s is the stone_id
// Warning: the square is assumed occupied
{
  Square * const to = &square[i][j];

	to->empty();

  const int player = s/MAX_NS;

	projected_dec(i,j,player);
	sumi[player] -= i;
	sumj[player] -= j;
	sumi2[player] -= sqr(i);
	sumj2[player] -= sqr(j);
	stone[s].avail_dirs = stone[s].captu_dirs = 0;
	nb_of_avail_moves[player] -= stone[s].nb_avail_dirs;
	nb_of_captu_moves[player] -= stone[s].nb_captu_dirs;
	stone[s].nb_avail_dirs = stone[s].nb_captu_dirs = 0;
	//hash_index_key -= hash_index_basis[i-1][j-1]*(player+1);
	//hash_clash_key -= hash_clash_basis[i-1][j-1]*(player+1);

  --nb_of_components[player];

  const int playerMask = player_mask(s);
  
  if(stone[s].root == s) {
    for(int dir=7; dir>=0; --dir) {
      Square * const neighbour_square = to+DP[dir];

      if(neighbour_square->is_friendly_occupied(playerMask)){
        const int neighbour_stone = neighbour_square->stone_id();

        if(stone[neighbour_stone].root == s) {
          ++nb_of_components[player];
          rooting_inventory(neighbour_stone);
        }
        if(dir&1) --dir;
        --dir;
      }
    }
  }
  else {
    const int last_component_id = new_component_id;

    // First check if a local disconnection is occuring
    // because there will be nothing to do if not
    int neighbour_mask = 0;
    
    for(int dir=7; dir>=0; --dir) {
      if((to+DP[dir])->is_friendly_occupied(playerMask)){
        neighbour_mask |= 1<<dir;
      }
    }
    
    if(nb_of_mergings[neighbour_mask]==0)
      ++nb_of_components[player];
    else if(nb_of_mergings[neighbour_mask]>0) {
      // Ok, we might actually be disconnecting a component
      // We'll thoroughly go through every candidate sub-component
      // (Is there a faster way?)
      for(int dir=7; dir>=0; --dir) {
        Square * const neighbour_square = to+DP[dir];

        if(neighbour_square->is_friendly_occupied(playerMask)){
          const int neighbour_stone = neighbour_square->stone_id();

          if(stone[neighbour_stone].component_id - last_component_id <= 0) {
            // We didn't go through that candidate sub-component yet
            ++nb_of_components[player];
            rooting_inventory(neighbour_stone);
          }
          if(dir&1) --dir;
          --dir;
       }
      }
    }
  }
}

#include <FL/Fl_Window.H>
Fl_Window *window;

void board_draw();

void stone_new(const int i, const int j, const int player) {
// i,j = 1,2,...,N , player = 0,1
	int s = free_stone_id[player]++;
	stone[s].is_on_board = true;
	stone[s].avail_dirs = stone[s].captu_dirs = 0;
	stone[s].nb_avail_dirs = stone[s].nb_captu_dirs = 0;
	++nb_of_stones[player];
	square_occupy(i,j,s);
	update_avail_dirs(i,j);
}

/*
    possible initial board setups:

5x5
    3           4           5           6           7           8
    . x x x .   . x x o .   . x x o .   . x x x .   . x x o .   . x x o .
    o . . . o   x . . . o   o . . . x   o . x . o   x . x . o   o . x . x
    o . . . o   o . . . o   o . . . o   o o . o o   o o . o o   o o . o o
    o . . . o   o . . . x   x . . . o   o . x . o   o . x . x   x . x . o
    . x x x .   . o x x .   . o x x .   . x x x .   . o x x .   . o x x .

6x6

    . x x x x .   . x x o o .   . x x x x .   . x x o o .
    o . . . . o   x . . . . o   o . x x . o   x . x o . o
    o . . . . o   x . . . . o   o o . . o o   x x . . o o
    o . . . . o   o . . . . x   o o . . o o   o o . . x x
    o . . . . o   o . . . . x   o . x x . o   o . o x . x
    . x x x x .   . o o x x .   . x x x x .   . o o x x .

7x7

    . x x x x x .   . x x x o o .   . . . . . . .   . . . . . . .
    o . . . . . o   x . . . . . o   . . x x x . .   . . x x o . .
    o . . . . . o   x . . . . . o   . o . . . o .   . x . . . o .
    o . . . . . o   o . . . . . o   . o . . . o .   . o . . . o .
    o . . . . . o   o . . . . . x   . o . . . o .   . o . . . x .
    o . . . . . o   o . . . . . x   . . x x x . .   . . o x x . .
    . x x x x x .   . o o x x x .   . . . . . . .   . . . . . . .

    . x x x x x .   . x x x o o .
    o . x x x . o   x . x x o . o
    o o . . . o o   x x . . . o o
    o o . . . o o   o o . . . o o
    o o . . . o o   o o . . . x x
    o . x x x . o   o . o x x . x
    . x x x x x .   . o o x x x .

8x8
 0                   3                   6
 . . . . . . . .     . x x x x x x .     . x x x x x x .
 . . x x x x . .     o . . . . . . o     o . x x x x . o
 . o . . . . o .     o . . . . . . o     o o . . . . o o
 . o . . . . o .     o . . . . . . o     o o . . . . o o
 . o . . . . o .     o . . . . . . o     o o . . . . o o
 . o . . . . o .     o . . . . . . o     o o . . . . o o
 . . x x x x . .     o . . . . . . o     o . x x x x . o
 . . . . . . . .     . x x x x x x .     . x x x x x x .

 1                   5                   7
 . . . . . . . .     . x x x o o o .     . x x x o o o .
 . . x x o o . .     x . . . . . . o     x . x x o o . o
 . x . . . . o .     x . . . . . . o     x x . . . . o o
 . x . . . . o .     x . . . . . . o     x x . . . . o o
 . o . . . . x .     o . . . . . . x     o o . . . . x x
 . o . . . . x .     o . . . . . . x     o o . . . . x x
 . . o o x x . .     o . . . . . . x     o . o o x x . x
 . . . . . . . .     . o o o x x x .     . o o o x x x .

 2                   6                   8
 . . . . . . . .     . x x x o o o .     . x x x o o o .
 . . x x o o . .     o . . . . . . x     o . x x o o . x
 . o . . . . x .     o . . . . . . x     o o . . . . x x
 . o . . . . x .     o . . . . . . x     o o . . . . x x
 . x . . . . o .     x . . . . . . o     x x . . . . o o
 . x . . . . o .     x . . . . . . o     x x . . . . o o
 . . o o x x . .     x . . . . . . o     x . o o x x . o
 . . . . . . . .     . o o o x x x .     . o o o x x x .

 
*/

void board_setup()
{
    if(INITIAL_SETUP>2) { // put 4N-8 stones along the edge
        if((INITIAL_SETUP%3)==0)
            for(int i=2; i<N; ++i) {
                stone_new(1,i,FIRST_PLAYER);
                stone_new(N,i,FIRST_PLAYER);
                stone_new(i,1,SECOND_PLAYER);
                stone_new(i,N,SECOND_PLAYER);
            }
        else if((INITIAL_SETUP%3)==1)
            for(int i=2; i<N; ++i) {
                stone_new(1,i,(i> (N+1)/2));
                stone_new(N,i,(i<= N/2   ));
                stone_new(i,1,(i>  N/2   ));
                stone_new(i,N,(i<=(N+1)/2));
            }
        else
            for(int i=2; i<N; ++i) {
                stone_new(1,i,(i> (N+1)/2));
                stone_new(N,i,(i<= N/2   ));
                stone_new(i,1,(i<=(N+1)/2));
                stone_new(i,N,(i>  N/2   ));
            }
    }
    if(INITIAL_SETUP/3!=1) { // put 4N-16 stones more inside
        if((INITIAL_SETUP%3)==0)
            for(int i=3; i<N-1; ++i) {
                stone_new( 2 , i ,FIRST_PLAYER);
                stone_new(N-1, i ,FIRST_PLAYER);
                stone_new( i , 2 ,SECOND_PLAYER);
                stone_new( i ,N-1,SECOND_PLAYER);
            }
        else if((INITIAL_SETUP%3)==1)
            for(int i=3; i<N-1; ++i) {
                stone_new( 2 , i ,(i> (N+1)/2));
                stone_new(N-1, i ,(i<= N/2   ));
                stone_new( i , 2 ,(i>  N/2   ));
                stone_new( i ,N-1,(i<=(N+1)/2));
            }
        else
            for(int i=3; i<N-1; ++i) {
                stone_new( 2 , i ,(i> (N+1)/2));
                stone_new(N-1, i ,(i<= N/2   ));
                stone_new( i , 2 ,(i<=(N+1)/2));
                stone_new( i ,N-1,(i>  N/2   ));
            }
    }
}

// -------------------------------------------------------------------

#include <FL/Fl.H>

bool time_is_out;
int nb_of_static_evals;
void mark_timeout(void *) {
  time_is_out = true;
}

// -------------------------------------------------------------------

int wanted_depth, reached_depth, missing_depth;
int strategy;

int enclosed;

int real_nc;

int line_eval(int *line, int *op_line, int len, const int delta) { // delta = len of minimal gap
  int comp[MAX_N*2];
  int nc = 0; // number of stone and gap components
  int no; // number of enclosed opponents
  
  comp[0] = 0;
  while((*line)==0) { if(--len==0) return 0; ++op_line, ++line; }
  do {
    comp[nc] += (*line);
    no = (*op_line++);
    while(--len && (*++line)) { comp[nc] += (*line); no += (*op_line++); }
    ++nc;
    enclosed += no;
    if(len == 0) break;
    comp[nc] = 1;
    no = (*op_line++);
    while(--len && (*++line)==0) { ++comp[nc];  no += (*op_line++); }
    if(len == 0) break;
    enclosed += no;
    if((comp[nc] /= delta)>0) comp[++nc] = 0;
    else --nc;
  } while(true);
  if(nc==1) return real_nc/2; // the projection is already connected

  comp[nc] = MAX_NS; // virtual gap past the last stone component
  int min_n_moves = MAX_N-2;
  for(int s0=0; s0<nc; s0+=2) { // s0 = first fixed stone component
    int n_moves = 0;
    int g = s0+1; // first gap component to fill
    int comp_g = comp[g];
    int s = 0;
    int comp_s = comp[0];
    
    while(s<s0) {
      const int d = min(comp_s,comp_g);
      if((n_moves += d)>=min_n_moves)
        return min_n_moves;// + max(real_nc+1-(nc+1)/2 - min_n_moves*(1+strategy), 0)/2;
      if((comp_s -= d)==0) comp_s = comp[s += 2];
      if((comp_g -= d)==0) comp_g = comp[g += 2];
    }
    comp_s = comp[s = nc-1];
    while(g<s) {
      const int d = min(comp_s,comp_g);
      if((n_moves += d)>=min_n_moves) break;
      if((comp_s -= d)==0) comp_s = comp[s -= 2];
      if((comp_g -= d)==0) comp_g = comp[g += 2];
    }
    if(n_moves<min_n_moves) min_n_moves = n_moves;
  }
  return min_n_moves;// + max(real_nc+1-(nc+1)/2 - min_n_moves*(1+strategy), 0)/2;
}

int player_eval(const int p) { // p == player 0 or 1
  const int op = p^1;

  real_nc = nb_of_components[p];
  
  const int m1 = line_eval(projected_1 [p], projected_1 [op], len_1 , 1);
  const int m3 = line_eval(projected_3 [p], projected_3 [op], len_1 , 1);
  const int m2 = line_eval(projected_2 [p], projected_2 [op], len_2 , 2);
  const int m4 = line_eval(projected_4 [p], projected_4 [op], len_2 , 2);
  const int m01= line_eval(projected_01[p], projected_01[op], len_01, 3);
  const int m12= line_eval(projected_12[p], projected_12[op], len_01, 3);
  const int m23= line_eval(projected_23[p], projected_23[op], len_01, 3);
  const int m34= line_eval(projected_34[p], projected_34[op], len_01, 3);

  return max(max(max(m1,m3),max(m2,m4)),max(max(m01,m12),max(m23,m34)));
}

const int GAMEOVER_THRESHOLD = 0x40000000L;

int board_eval() {

  if((++nb_of_static_evals&0x0000ffffL)==0) Fl::check();

  enclosed = 0;
  if(nb_of_components[0]==1 || nb_of_components[1]==1) {
    if(nb_of_components[player^1]==1)
      // The player who has just moved has just won
      return GAMEOVER_THRESHOLD+(15*(MAX_NS*16)+missing_depth)*(MAX_NS*8)+
        nb_of_components[player];
    // Else, he has just stupidly made the next player win
    return -GAMEOVER_THRESHOLD-(15*(MAX_NS*16)+missing_depth)*(MAX_NS*8)-
      nb_of_components[player^1];
  }
  const int ope = player_eval(player^1);
  enclosed = -enclosed;
  const int pe = player_eval(player);
  return ((pe-ope)*2+enclosed)*(MAX_NS*8)+
    nb_of_avail_moves[player^1]-nb_of_avail_moves[player];
}

// int current_board_val;

// -------------------------------------------------------------------

inline bool can_move_along(const int stone_id, const int dir) {
  return  stone_id/64==player && // the stone belongs to the player to move
    stone[stone_id].is_on_board && // the stone is on the board
   (stone[stone_id].avail_dirs&(1<<dir)) // the direction is available
  ;
}

class Move {
public:
	int from_row, from_col;
	int to_row, to_col;
	int stone_id, dir, dist;
	int captured_stone_id;	// <0 if no capture
	int value;
	
  bool operator< (const Move& m2) const { return value < m2.value; };
  bool operator== (const Move& m2) const { return value == m2.value; };

  void expand(const int s, const int d) { // this assumes the move is valid
    stone_id = s;
    dir = d;
    from_row = stone[stone_id].row;
    from_col = stone[stone_id].col;
    switch(dir) {
    case 0: dist = count_4[coord_project_0(from_row,from_col)]; break;
    case 1: dist = count_1[coord_project_1(from_row,from_col)]; break;
    case 2: dist = count_2[coord_project_2(from_row,from_col)]; break;
    case 3: dist = count_3[coord_project_3(from_row,from_col)]; break;
    case 4: dist = count_4[coord_project_4(from_row,from_col)]; break;
    case 5: dist = count_1[coord_project_5(from_row,from_col)]; break;
    case 6: dist = count_2[coord_project_6(from_row,from_col)]; break;
    case 7: dist = count_3[coord_project_7(from_row,from_col)]; break;
    }
    to_row = from_row + dist*DI[dir];
    to_col = from_col + dist*DJ[dir];
    captured_stone_id = square[to_row][to_col].stone_id();
  }

	int apply() const {
    square_empty(from_row, from_col, stone_id);
    update_avail_dirs(from_row,from_col);

    if(captured_stone_id>=0) {
      square_empty(to_row, to_col, captured_stone_id);
      stone[captured_stone_id].is_on_board = false;
    	--nb_of_stones[player^1];
    }
    square_occupy(to_row,to_col, stone_id);
    update_avail_dirs(to_row, to_col);
    player ^= 1;

  };
  
  void undo() const {
    player ^= 1;
    square_empty(to_row,to_col, stone_id);
    if(captured_stone_id>=0) {
      square_occupy(to_row, to_col, captured_stone_id);
      stone[captured_stone_id].is_on_board = true;
    	++nb_of_stones[player^1];
    }
    update_avail_dirs(to_row, to_col);

    square_occupy(from_row, from_col, stone_id);
    update_avail_dirs(from_row,from_col);
  };
  
  void print(char *s) {
    *s++ = '@'+from_col;
    if(from_row>9) *s++ = '1';
    *s++ = '0'+(from_row%10);
    *s++ = (captured_stone_id>=0)? 'x': '-';
    *s++ = '@'+to_col;
    if(to_row>9) *s++ = '1';
    *s++ = '0'+(to_row%10);
    *s = 0;
  }
};

// -------------------------------------------------------------------

Move recommended_move;

Move previous_move, current_move;

Move played_move[500];
int nb_of_played_moves, current_move_number;

void game_new()
{
  player = 0;

  previous_move.from_row = previous_move.from_col =
  previous_move.to_row = previous_move.to_col =
  current_move.from_row = current_move.from_col =
  current_move.to_row = current_move.to_col = 0;

  nb_of_played_moves = current_move_number = 0;

  // current_board_val = board_eval();
}


// -------------------------------------------------------------------

typedef std::priority_queue<Move> Move_List;

/*
class Move_List {
  Move top_move;
public:
  Move_List() { top_move.value = -1000000; };
  Move top() const { return top_move; };
  void push(const Move &m) { if(m.value>top_move.value) top_move = m; };
};
*/

inline void queue_move(Move_List &ml, Move &m) {
  m.to_row = m.from_row + m.dist*DI[m.dir];
  m.to_col = m.from_col + m.dist*DJ[m.dir];
  m.captured_stone_id = square[m.to_row][m.to_col].stone_id();
  m.apply();
  m.value = board_eval();
  m.undo();
  ml.push(m);
}

inline void queue_if_improving(Move_List &ml, Move &m, const int current_val) {
  m.to_row = m.from_row + m.dist*DI[m.dir];
  m.to_col = m.from_col + m.dist*DJ[m.dir];
  m.captured_stone_id = square[m.to_row][m.to_col].stone_id();
  m.apply();
  m.value = board_eval();
  m.undo();
  if(m.value>current_val)
    ml.push(m);
}

void queue_all_improving_captures(Move_List &ml, const int v) {
  Move m;
  for(m.stone_id = player*MAX_NS; m.stone_id<free_stone_id[player]; ++m.stone_id)
  if(stone[m.stone_id].nb_captu_dirs) {
    m.from_row = stone[m.stone_id].row;
    m.from_col = stone[m.stone_id].col;
    if(current_move_number==0 && reached_depth==0 &&
      (m.from_row>=(N+1)/2 || m.from_col>(N+1)/2))
      continue;
    const int dirs = stone[m.stone_id].captu_dirs;
    if(dirs &  1) { m.dir = 0; m.dist = count_4[coord_project_0(m.from_row,m.from_col)]; queue_if_improving(ml,m,v); }
    if(dirs &  2) { m.dir = 1; m.dist = count_1[coord_project_1(m.from_row,m.from_col)]; queue_if_improving(ml,m,v); }
    if(dirs &  4) { m.dir = 2; m.dist = count_2[coord_project_2(m.from_row,m.from_col)]; queue_if_improving(ml,m,v); }
    if(dirs &  8) { m.dir = 3; m.dist = count_3[coord_project_3(m.from_row,m.from_col)]; queue_if_improving(ml,m,v); }
    if(dirs & 16) { m.dir = 4; m.dist = count_4[coord_project_4(m.from_row,m.from_col)]; queue_if_improving(ml,m,v); }
    if(dirs & 32) { m.dir = 5; m.dist = count_1[coord_project_5(m.from_row,m.from_col)]; queue_if_improving(ml,m,v); }
    if(dirs & 64) { m.dir = 6; m.dist = count_2[coord_project_6(m.from_row,m.from_col)]; queue_if_improving(ml,m,v); }
    if(dirs &128) { m.dir = 7; m.dist = count_3[coord_project_7(m.from_row,m.from_col)]; queue_if_improving(ml,m,v); }
  }
}

void queue_all_non_captures(Move_List &ml) {
  Move m;
  for(m.stone_id = player*MAX_NS; m.stone_id<free_stone_id[player]; ++m.stone_id)
  if(stone[m.stone_id].nb_avail_dirs > stone[m.stone_id].nb_captu_dirs) {
    m.from_row = stone[m.stone_id].row;
    m.from_col = stone[m.stone_id].col;
    if(current_move_number==0 && reached_depth==0 &&
      (m.from_row>=(N+1)/2 || m.from_col>(N+1)/2))
      continue;
    const int dirs = stone[m.stone_id].avail_dirs ^ stone[m.stone_id].captu_dirs;
    if(dirs &  1) { m.dir = 0; m.dist = count_4[coord_project_0(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs &  2) { m.dir = 1; m.dist = count_1[coord_project_1(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs &  4) { m.dir = 2; m.dist = count_2[coord_project_2(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs &  8) { m.dir = 3; m.dist = count_3[coord_project_3(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs & 16) { m.dir = 4; m.dist = count_4[coord_project_4(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs & 32) { m.dir = 5; m.dist = count_1[coord_project_5(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs & 64) { m.dir = 6; m.dist = count_2[coord_project_6(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs &128) { m.dir = 7; m.dist = count_3[coord_project_7(m.from_row,m.from_col)]; queue_move(ml,m); }
  }
}

void queue_all_moves(Move_List &ml) {
  Move m;
  for(m.stone_id = player*MAX_NS; m.stone_id<free_stone_id[player]; ++m.stone_id)
  if(stone[m.stone_id].avail_dirs) {
    m.from_row = stone[m.stone_id].row;
    m.from_col = stone[m.stone_id].col;
    if(current_move_number==0 && reached_depth==0 &&
      (m.from_row>=(N+1)/2 || m.from_col>(N+1)/2))
      continue;
    const int dirs = stone[m.stone_id].avail_dirs;
    if(dirs &  1) { m.dir = 0; m.dist = count_4[coord_project_0(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs &  2) { m.dir = 1; m.dist = count_1[coord_project_1(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs &  4) { m.dir = 2; m.dist = count_2[coord_project_2(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs &  8) { m.dir = 3; m.dist = count_3[coord_project_3(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs & 16) { m.dir = 4; m.dist = count_4[coord_project_4(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs & 32) { m.dir = 5; m.dist = count_1[coord_project_5(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs & 64) { m.dir = 6; m.dist = count_2[coord_project_6(m.from_row,m.from_col)]; queue_move(ml,m); }
    if(dirs &128) { m.dir = 7; m.dist = count_3[coord_project_7(m.from_row,m.from_col)]; queue_move(ml,m); }
  }
}

inline void quiet_check(Move &m0, int alpha, int beta, int cv) {
  m0.to_row = m0.from_row + m0.dist*DI[m0.dir];
  m0.to_col = m0.from_col + m0.dist*DJ[m0.dir];
  m0.captured_stone_id = square[m0.to_row][m0.to_col].stone_id();
  m0.apply();
  m0.value = board_eval();
/*
  if(m0.value>cv) {
    Move m;
  	Move best_move;
    best_move.value = -m0.value;
    for(m.stone_id = player*MAX_NS; m.stone_id<free_stone_id[player]; ++m.stone_id)
    if(stone[m.stone_id].nb_captu_dirs) {
      m.from_row = stone[m.stone_id].row;
      m.from_col = stone[m.stone_id].col;
      const int dirs = stone[m.stone_id].captu_dirs;
      if(dirs &  1) { m.dir = 0; m.dist = count_4[coord_project_0(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, -m0.value); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs &  2) { m.dir = 1; m.dist = count_1[coord_project_1(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, -m0.value); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs &  4) { m.dir = 2; m.dist = count_2[coord_project_2(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, -m0.value); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs &  8) { m.dir = 3; m.dist = count_3[coord_project_3(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, -m0.value); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs & 16) { m.dir = 4; m.dist = count_4[coord_project_4(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, -m0.value); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs & 32) { m.dir = 5; m.dist = count_1[coord_project_5(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, -m0.value); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs & 64) { m.dir = 6; m.dist = count_2[coord_project_6(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, -m0.value); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs &128) { m.dir = 7; m.dist = count_3[coord_project_7(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, -m0.value); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
    }
    m0.value = -best_move.value;
  }
*/
  m0.undo();
}

int evaluate(int alpha, int beta, int cv) {
	if(missing_depth==1) {	// one node from a leaf, no deep search to do
    Move m;
  	Move best_move;
  	best_move.value = -INFI;
    for(m.stone_id = player*MAX_NS; m.stone_id<free_stone_id[player]; ++m.stone_id)
    if(stone[m.stone_id].is_on_board && stone[m.stone_id].avail_dirs) {
      m.from_row = stone[m.stone_id].row;
      m.from_col = stone[m.stone_id].col;
      const int dirs = stone[m.stone_id].avail_dirs;
      if(dirs &  1) { m.dir = 0; m.dist = count_4[coord_project_0(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, cv); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs &  2) { m.dir = 1; m.dist = count_1[coord_project_1(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, cv); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs &  4) { m.dir = 2; m.dist = count_2[coord_project_2(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, cv); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs &  8) { m.dir = 3; m.dist = count_3[coord_project_3(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, cv); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs & 16) { m.dir = 4; m.dist = count_4[coord_project_4(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, cv); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs & 32) { m.dir = 5; m.dist = count_1[coord_project_5(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, cv); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs & 64) { m.dir = 6; m.dist = count_2[coord_project_6(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, cv); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
      if(dirs &128) { m.dir = 7; m.dist = count_3[coord_project_7(m.from_row,m.from_col)]; quiet_check(m, alpha, beta, cv); if(m.value>best_move.value) { best_move = m; if(m.value>=beta) break; if(m.value>alpha) alpha = m.value; } }
    }
    if(reached_depth==0)  recommended_move = best_move;
    return best_move.value;
  }

	Move_List move_list;
  if(cv == -INFI)
    cv = -board_eval();

	Move best_move;
	int best_val = -INFI;
	int nm = missing_depth + 12;
// int best_conn = -INFI;

  queue_all_moves(move_list);

  {
  	while(!move_list.empty() && --nm) {
      Move move = move_list.top();
      move_list.pop();
/*
      const int conn = (move.value + (MAX_NS*8*MAX_NS*8)) / (MAX_NS*16*MAX_NS*8);
  		if(conn<best_conn-((missing_depth-1)&14)) {
        recommended_move = best_move;
        return best_val;
      }
*/    int val = move.value;
      if(val > -GAMEOVER_THRESHOLD && val < GAMEOVER_THRESHOLD) {
        move.apply();
        ++reached_depth; --missing_depth;
        val = -evaluate(-beta, -alpha, -val);
        ++missing_depth; --reached_depth;
        move.undo();
      }

      if(val>best_val) {
        best_val = val;
  			best_move = move;
  			if(val>=beta) break;
  			if(val>alpha) alpha = val;
//      best_conn = (val + (MAX_NS*8*MAX_NS*8)) / (MAX_NS*16*MAX_NS*8);
  		}

  		if(time_is_out) break;
  	}
  }

  best_move.value = best_val;
  if(reached_depth==0)	recommended_move = best_move;
	return best_val;
}

#include <FL/Fl_Output.H>
Fl_Output *thinking_move_output, *thinking_depth_output;

int    max_depth[2];
double max_time [2];

void think() {
  strategy = player;
  time_is_out = false;
  nb_of_static_evals = 0;

  if(max_time[player]>0) {
    Fl::add_timeout(max_time[player], mark_timeout);

    thinking_move_output->label("exploring ");
    thinking_move_output->show();
    thinking_depth_output->show();

    Move_List move_list[2];
    int flipflop = 0;
    reached_depth = 0;
    queue_all_moves(move_list[flipflop]);
    recommended_move = move_list[flipflop].top();

    for(wanted_depth = 3; wanted_depth<=max_depth[player]; wanted_depth+=2) {

      Fl::check();
      if(time_is_out) {
        recommended_move = move_list[flipflop].top();
        break;
      }
      
      missing_depth = wanted_depth-(reached_depth = 1);

      Move best_move;
      best_move.value = -INFI;
      int nm = 12+1+missing_depth;
      int mn = 0;
      
      while(!move_list[flipflop].empty()) {
        ++mn;
        Move move = move_list[flipflop].top();
        move_list[flipflop].pop();
        if(--nm>0) {
        if(move.value > -GAMEOVER_THRESHOLD && move.value < GAMEOVER_THRESHOLD)
        {
          char move_string[12];
          move_string[0] = mn<10? ' ': '0'+mn/10;
          move_string[1] = '0'+mn%10;
          move_string[2] = ':';
          move_string[3] = ' ';
          move.print(move_string+4);
          thinking_move_output->value(move_string);
          thinking_move_output->redraw();
          
          if(wanted_depth>9) {
            move_string[0] = '0'+wanted_depth/10;
            move_string[1] = '0'+wanted_depth%10;
            move_string[2] = 0;
          }
          else {
            move_string[0] = '0'+wanted_depth;
            move_string[1] = 0;
          }
          thinking_depth_output->value(move_string);
          thinking_depth_output->redraw();

          move.apply();
          move.value = -evaluate(-GAMEOVER_THRESHOLD, -best_move.value, -INFI);
          move.undo();
        }
        if(time_is_out) {
          recommended_move = move_list[flipflop^1].empty()?
            move:
            move_list[flipflop^1].top();
          break;
        }
		    if(move.value>best_move.value) {
    			recommended_move = best_move = move;
    			if(move.value>=GAMEOVER_THRESHOLD) nm=0;
    		}
        }
        else
          move.value -= (MAX_NS*16*16*MAX_NS*8);
        move_list[flipflop^1].push(move);
    	}
    	if(time_is_out) break;
      flipflop ^= 1;
    }
    Fl::remove_timeout(mark_timeout);
    thinking_move_output->hide();
    thinking_depth_output->hide();
  }
  else {
    reached_depth = 0;
  	missing_depth = max_depth[player];

    evaluate(-GAMEOVER_THRESHOLD, GAMEOVER_THRESHOLD, -INFI);
  }
}

// -------------------------------------------------------------------

#include <FL/Fl_Box.H>
#include <FL/Fl_Button.H>
#include <FL/Fl_Image.H>
#include <FL/Fl_Input.H>

uchar *square_shot[3][2][2][2]; // [content][up?][remember?][highlight?]
Fl_RGB_Image *square_image[3][2][2][2];


// -------------------------------------------------------------------

double (*light)[9][3];
int n_lights = 0;

void light_new()
{
    light = new double[9][9][3];
    
    for(int li=-4; li<=4; ++li) for(int lj=-4; lj<=4; ++lj)
        if(li*li+lj*lj<25) {
            light[li+4][lj+4][0] = cos(theta+delta*lj)*cos(alpha+delta*li);
            light[li+4][lj+4][1] = cos(theta+delta*lj)*sin(alpha+delta*li);
            light[li+4][lj+4][2] = sin(theta+delta*lj);
            ++n_lights;
        }
}

void light_delete()
{
    delete[] light;
}

Fl_RGB_Image* shoot(uchar * &shot, Fl_RGB_Image * &image,
    const int W, const double v, // square Width, relative vertical radius (+-)
    const int R, const int G, const int B, // square Red, Green, Blue
    const double direct_light
)
{
    shot = new uchar[W*W*3];

    uchar* p = shot;
    for(int j=0; j<W; j++) for (int i=0; i<W; i++) {
        double pixel_R = 0, pixel_G = 0, pixel_B = 0;
        for(int jj=0; jj<4; jj++) for(int ii=0; ii<4; ii++) {
            const double  y = -(j*4-W*2+jj+0.5)/2/W,
                          x =  (i*4-W*2+ii+0.5)/2/W;

            const double xq = sqrt(1-x*x);
            const double yq = sqrt(1-y*y);
            const double z = v*xq*yq;

            double a = v*x*yq/xq; // get the normal vector
            double b = v*y*xq/yq;
            const double c = 1/sqrt(a*a+b*b+1);
            a *= c;
            b *= c;

            double s = AMBIENT;

            for(int li=-4; li<=4; ++li) for(int lj=-4; lj<=4; ++lj)
                if(li*li+lj*lj<25) {
                    s += (
                        a*light[li+4][lj+4][0]+
                        b*light[li+4][lj+4][1]+
                        c*light[li+4][lj+4][2]
                    )*direct_light/n_lights;
                }

            pixel_R += R*s;
            pixel_G += G*s;
            pixel_B += B*s;
        }
        *(p++) = uchar(min(255,int(ceil(pixel_R/16))));
        *(p++) = uchar(min(255,int(ceil(pixel_G/16))));
        *(p++) = uchar(min(255,int(ceil(pixel_B/16))));
    }

    image = new Fl_RGB_Image (shot, W, W, 3, 0);
}

void shoot(uchar * &shot, Fl_RGB_Image * &image,
    const int W, const double v, // square Width, relative vertical radius (+-)
    const int R, const int G, const int B, // square Red, Green, Blue
    const int sW, const double sv, // stone Width, relative vertical radius
    const int sR, const int sG, const int sB, // stone Red, Green, Blue
    const double direct_light
)
{
    shot = new uchar[W*W*3];

    uchar* p = shot;
    for(int j=0; j<W; j++) for (int i=0; i<W; i++) {
        double pixel_R = 0, pixel_G = 0, pixel_B = 0;
        for(int jj=0; jj<4; jj++) for(int ii=0; ii<4; ii++) {
            const double  y = -(j*4-W*2+jj+0.5)/2/W,
                          x =  (i*4-W*2+ii+0.5)/2/W;
            const double sy = -(j*4-W*2+jj+0.5+((W^sW)&1)*2)/2/sW,
                         sx =  (i*4-W*2+ii+0.5+((W^sW)&1)*2)/2/sW;
            const double d2 = sx*sx+sy*sy;

            if(d2<1.) {
                const double q = sqrt(1-d2);
                double a = sv*sx/q;
                double b = sv*sy/q;
                const double c = 1/sqrt(a*a+b*b+1);
                a *= c;
                b *= c;

                double s = AMBIENT;

                for(int li=-4; li<=4; ++li) for(int lj=-4; lj<=4; ++lj)
                    if(li*li+lj*lj<25) {
                        s += (
                            a*light[li+4][lj+4][0]+
                            b*light[li+4][lj+4][1]+
                            c*light[li+4][lj+4][2]
                        )*direct_light/n_lights;
                    }

                const double aa = a*c*2; // get the reflected light vector
                const double bb = b*c*2; // (twice as far from noon as the normal vector)
                const double cc = c*c*2-1;
                if(
                    aa*light[4][4][0]+
                    bb*light[4][4][1]+
                    cc*light[4][4][2]
                    > cos_5delta
                ) s += 0.1;

                pixel_R += sR*s;
                pixel_G += sG*s;
                pixel_B += sB*s;
            }

            else {
                const double xq = sqrt(1-x*x);
                const double yq = sqrt(1-y*y);
                const double z = v*xq*yq;

                double a = v*x*yq/xq;
                double b = v*y*xq/yq;
                const double c = 1/sqrt(a*a+b*b+1);
                a *= c;
                b *= c;

                double s = AMBIENT;

                for(int li=-4; li<=4; ++li) for(int lj=-4; lj<=4; ++lj)
                    if(li*li+lj*lj<25) {
                        const double dz = (sv + ((v>0)? v-z: v-z))
                            /light[li+4][lj+4][2];
                        const double xx = sx + dz*light[li+4][lj+4][0];
                        const double yy = sy + dz*light[li+4][lj+4][1];

                        if(xx*xx+yy*yy>=1) {
                            s += (
                                a*light[li+4][lj+4][0]+
                                b*light[li+4][lj+4][1]+
                                c*light[li+4][lj+4][2]
                            )*direct_light/n_lights;
                        }
                    }

                pixel_R += R*s;
                pixel_G += G*s;
                pixel_B += B*s;
            }
        }
        *(p++) = uchar(min(255,int(ceil(pixel_R/16))));
        *(p++) = uchar(min(255,int(ceil(pixel_G/16))));
        *(p++) = uchar(min(255,int(ceil(pixel_B/16))));
    }

    image = new Fl_RGB_Image (shot, W, W, 3, 0);
}

//    const uchar ground_color[3] = {236, 241, 241 };
//    const uchar ball_color[3] = {255, 224, 197 };
//    const uchar ball_color[3] = {170, 75, 1 };

void square_shoot() {
  for(int content=0; content<3; ++content)
  for(int up=0; up<2; ++up)
  for(int remember=0; remember<2; ++remember)
  for(int highlight=0; highlight<2; ++highlight)
  if(content==0)
    shoot(
      square_shot [0][up][remember][highlight],
      square_image[0][up][remember][highlight],
      SQUARE_WIDTH,
      SQUARE_THICKNESS[up],
      SQUARE_COLOR[remember][0],
      SQUARE_COLOR[remember][1],
      SQUARE_COLOR[remember][2],
      DIRECT_LIGHT[up][highlight]
    );
  else
    shoot(
      square_shot [content][up][remember][highlight],
      square_image[content][up][remember][highlight],
      SQUARE_WIDTH,
      SQUARE_THICKNESS[up],
      SQUARE_COLOR[remember][0],
      SQUARE_COLOR[remember][1],
      SQUARE_COLOR[remember][2],
       STONE_WIDTH,
       STONE_THICKNESS[up],
       STONE_COLOR[content-1][0],
       STONE_COLOR[content-1][1],
       STONE_COLOR[content-1][2],
      DIRECT_LIGHT[up][highlight]
    );
}

// --------------------------------------------------------------------------

class FL_EXPORT Think_Button : public Fl_Button {
public:
  Think_Button(void)
  : Fl_Button(N*SQUARE_WIDTH+150, 50, 45, 25, "Think!") {
  };
  int handle(int event);
};

class FL_EXPORT Restart_Button : public Fl_Button {
public:
  Restart_Button(void)
  : Fl_Button(15, N*SQUARE_WIDTH+20, 25, 25, "@|<") {
    //this->labeltype(FL_ENGRAVED_LABEL);
  };
  int handle(int event);
};

class FL_EXPORT Undo_Button : public Fl_Button {
public:
  Undo_Button(void)
  : Fl_Button(50, N*SQUARE_WIDTH+20, 25, 25, "@<-") {
    //this->labeltype(FL_ENGRAVED_LABEL);
  };
  int handle(int event);
};

class FL_EXPORT Redo_Button : public Fl_Button {
public:
  Redo_Button(void)
  : Fl_Button(100, N*SQUARE_WIDTH+20, 25, 25, "@->") {
    //this->labeltype(FL_ENGRAVED_LABEL);
  };
  int handle(int event);
};

class FL_EXPORT GoToEnd_Button : public Fl_Button {
public:
  GoToEnd_Button(void)
  : Fl_Button(135, N*SQUARE_WIDTH+20, 25, 25, "@>|") {
    //this->labeltype(FL_ENGRAVED_LABEL);
  };
  int handle(int event);
};

// --------------------------------------------------------------------------

class FL_EXPORT Square_Button : public Fl_Button {
  int content, up, remember, highlight;
public:
  int row, col;
  Square_Button(
    int r, int c,
    int x, int y, int w, int h, const char *label = 0
  ) : Fl_Button(x, y, w, h, label) {
    row = r; col = c;
  };
  int handle(int event);
  void light_set(const int c, const int u, const int r, const int hi) {
    content = c; up = u; remember = r; highlight = hi;
  }
  void image_set() {
    Fl_Button::image(square_image[content][up][remember][highlight]);
  };
};


Fl_Box *board_box;
Square_Button *square_button[MAX_N][MAX_N];
Fl_Box *square_box[MAX_N][MAX_N];

Fl_Box
  *projconn_box[2],
  *compnumb_box[2],
  *enclosed_box[2],
  *stonnumb_box[2],
  *captures_box[2],
  *mobility_box[2];
char
  projconn_label[2][3],
  compnumb_label[2][3],
  enclosed_label[2][4],
  stonnumb_label[2][3],
  captures_label[2][4],
  mobility_label[2][4];

#include <FL/Fl_Value_Input.H>

Fl_Value_Input *depth_input, *time_input;
Fl_Box   *depth_unit, *time_unit;
Think_Button *think_button;
Restart_Button *restart_button;
Undo_Button *undo_button;
Redo_Button *redo_button;
GoToEnd_Button *gotoend_button;

bool thinking = false;

void board_box_new()
{
  board_box = new Fl_Box (4, 4, N*SQUARE_WIDTH+4, N*SQUARE_WIDTH+4);
  board_box->box(FL_UP_BOX);
  for(int i=0; i<N; ++i)
    for(int j=0; j<N; ++j) {
      square_box[i][j] = new Fl_Box(6+SQUARE_WIDTH*j, 6+SQUARE_WIDTH*i, SQUARE_WIDTH, SQUARE_WIDTH);
      square_button[i][j] = new Square_Button(
        i+1, j+1,
        6+SQUARE_WIDTH*j, 6+SQUARE_WIDTH*i, SQUARE_WIDTH, SQUARE_WIDTH
      );
    }

  for(int p = 0; p<2; p++) {
    projconn_box[p] = new Fl_Box(FL_UP_BOX,N*SQUARE_WIDTH+15+35*p,  5, 32, 16, 0);
    compnumb_box[p] = new Fl_Box(FL_UP_BOX,N*SQUARE_WIDTH+15+35*p, 24, 32, 16, 0);
    enclosed_box[p] = new Fl_Box(FL_UP_BOX,N*SQUARE_WIDTH+15+35*p, 50, 32, 16, 0);
    stonnumb_box[p] = new Fl_Box(FL_UP_BOX,N*SQUARE_WIDTH+15+35*p, 69, 32, 16, 0);
    captures_box[p] = new Fl_Box(FL_UP_BOX,N*SQUARE_WIDTH+15+35*p, 95, 32, 16, 0);
    mobility_box[p] = new Fl_Box(FL_UP_BOX,N*SQUARE_WIDTH+15+35*p,114, 32, 16, 0);
}

  depth_input = new Fl_Value_Input(N*SQUARE_WIDTH+160, 5, 22, 20, "max depth ");
  depth_unit  = new Fl_Box  (N*SQUARE_WIDTH+180, 5, 60, 20, "levels");
  depth_input->step(1);
  depth_input->value(30);
  depth_input->bounds(1, 30);
  time_input  = new Fl_Value_Input(N*SQUARE_WIDTH+150, 25, 42, 20, "max time ");
  time_unit   = new Fl_Box  (N*SQUARE_WIDTH+190, 25, 60, 20, "seconds");
  time_input->step(1.);
  time_input->value(5.);
  time_input->bounds(0., 3600.*25*16);
  think_button = new Think_Button();

  thinking_move_output = new Fl_Output(N*SQUARE_WIDTH+80,135, 70, 20, "exploring ");
  thinking_move_output->hide();
  thinking_depth_output= new Fl_Output(N*SQUARE_WIDTH+215,135, 22, 20, "at depth ");
  thinking_depth_output->hide();
  
  restart_button = new Restart_Button();
  undo_button = new Undo_Button();
  redo_button = new Redo_Button();
  gotoend_button = new GoToEnd_Button();
}

void half_move_draw()
{
    for(int i=1; i<=N; ++i)
        for(int j=1; j<=N; ++j) {
            const int content = square[i][j].short_content();
            int up =
              (current_move.from_row==i && current_move.from_col==j);
            const int remember =
                (current_move.from_row==i && current_move.from_col==j);
            const int highlight = 0;
            
            if(stone[current_move.stone_id].avail_dirs&1 &&
              i == current_move.from_row + DI[0]*
                count_4[coord_project_4(current_move.from_row,current_move.from_col)] &&
              j == current_move.from_col + DJ[0]*
                count_4[coord_project_4(current_move.from_row,current_move.from_col)]
            ) up = 1;
            else
            if(stone[current_move.stone_id].avail_dirs&2 &&
              i == current_move.from_row + DI[1]*
                count_1[coord_project_1(current_move.from_row,current_move.from_col)] &&
              j == current_move.from_col + DJ[1]*
                count_1[coord_project_1(current_move.from_row,current_move.from_col)]
            ) up = 1;
            else
            if(stone[current_move.stone_id].avail_dirs&4 &&
              i == current_move.from_row + DI[2]*
                count_2[coord_project_2(current_move.from_row,current_move.from_col)] &&
              j == current_move.from_col + DJ[2]*
                count_2[coord_project_2(current_move.from_row,current_move.from_col)]
            ) up = 1;
            else
            if(stone[current_move.stone_id].avail_dirs&8 &&
              i == current_move.from_row + DI[3]*
                count_3[coord_project_3(current_move.from_row,current_move.from_col)] &&
              j == current_move.from_col + DJ[3]*
                count_3[coord_project_3(current_move.from_row,current_move.from_col)]
            ) up = 1;
            else
            if(stone[current_move.stone_id].avail_dirs&16 &&
              i == current_move.from_row + DI[4]*
                count_4[coord_project_4(current_move.from_row,current_move.from_col)] &&
              j == current_move.from_col + DJ[4]*
                count_4[coord_project_4(current_move.from_row,current_move.from_col)]
            ) up = 1;
            else
            if(stone[current_move.stone_id].avail_dirs&32 &&
              i == current_move.from_row + DI[5]*
                count_1[coord_project_1(current_move.from_row,current_move.from_col)] &&
              j == current_move.from_col + DJ[5]*
                count_1[coord_project_1(current_move.from_row,current_move.from_col)]
            ) up = 1;
            else
            if(stone[current_move.stone_id].avail_dirs&64 &&
              i == current_move.from_row + DI[6]*
                count_2[coord_project_2(current_move.from_row,current_move.from_col)] &&
              j == current_move.from_col + DJ[6]*
                count_2[coord_project_2(current_move.from_row,current_move.from_col)]
            ) up = 1;
            else
            if(stone[current_move.stone_id].avail_dirs&128 &&
              i == current_move.from_row + DI[7]*
                count_3[coord_project_3(current_move.from_row,current_move.from_col)] &&
              j == current_move.from_col + DJ[7]*
                count_3[coord_project_3(current_move.from_row,current_move.from_col)]
            ) up = 1;

            if(up) {
              square_button[i-1][j-1]->light_set(content,up,remember,highlight);
              square_button[i-1][j-1]->image_set();
              square_button[i-1][j-1]->show();
            }
            else
            {
              square_box[i-1][j-1]->image(
                square_image[content][up][remember][highlight]
              );
              square_button[i-1][j-1]->hide();
            }
        }
}


void board_draw()
{
  for(int i=1; i<=N; ++i)
    for(int j=1; j<=N; ++j) {
      const int content = square[i][j].short_content();
      const int up = (content==player+1)&&(nb_of_components[0]>1)&&(nb_of_components[1]>1);
      const int remember =
        (previous_move.from_row==i && previous_move.from_col==j) ||
        (previous_move.to_row==i && previous_move.to_col==j) ||
        (current_move.from_row==i && current_move.from_col==j);
      const int highlight = 0;

      if(up) {
        square_button[i-1][j-1]->light_set(content,up,remember,highlight);
        square_button[i-1][j-1]->image_set();
        square_button[i-1][j-1]->show();
      }
      else
      {
        square_box[i-1][j-1]->image(
          square_image[content][up][remember][highlight]
        );
        square_button[i-1][j-1]->hide();
      }
    }

  if(current_move_number>0) {
    restart_button->show();
    undo_button->show();
  }
  else {
    restart_button->hide();
    undo_button->hide();
  }
  if(current_move_number<nb_of_played_moves) {
    redo_button->show();
    gotoend_button->show();
  }
  else {
    redo_button->hide();
    gotoend_button->hide();
  }

  for(int p = 1; p>=0; --p) {
    enclosed = 0;
    int projconn = player_eval(p);
    if(projconn<0) projconn_label[p][0] = projconn_label[p][1] = '-';
    else {
      projconn_label[p][0] = projconn/10 + '0';
      projconn_label[p][1] = projconn%10 + '0';
    }
    projconn_label[p][2] = 0;
    projconn_box[p]->label(projconn_label[p]);

    compnumb_label[p][0] = nb_of_components[p]/10 + '0';
    compnumb_label[p][1] = nb_of_components[p]%10 + '0';
    compnumb_label[p][2] = 0;
    compnumb_box[p]->label(compnumb_label[p]);

    enclosed_label[p^1][0] = enclosed/100 + '0';
    enclosed_label[p^1][1] = enclosed/10%10 + '0';
    enclosed_label[p^1][2] = enclosed%10 + '0';
    enclosed_label[p^1][3] = 0;
    enclosed_box[p^1]->label(enclosed_label[p^1]);

    stonnumb_label[p][0] = nb_of_stones[p]/10 + '0';
    stonnumb_label[p][1] = nb_of_stones[p]%10 + '0';
    stonnumb_label[p][2] = 0;
    stonnumb_box[p]->label(stonnumb_label[p]);

    captures_label[p][0] = nb_of_captu_moves[p]/100 + '0';
    captures_label[p][1] = nb_of_captu_moves[p]/10%10 + '0';
    captures_label[p][2] = nb_of_captu_moves[p]%10 + '0';
    captures_label[p][3] = 0;
    captures_box[p]->label(captures_label[p]);

    mobility_label[p][0] = nb_of_avail_moves[p]/100 + '0';
    mobility_label[p][1] = nb_of_avail_moves[p]/10%10 + '0';
    mobility_label[p][2] = nb_of_avail_moves[p]%10 + '0';
    mobility_label[p][3] = 0;
    mobility_box[p]->label(mobility_label[p]);

  }

}

// -------------------------------------------------------------------------

int Square_Button::handle(int event) {
  if(thinking)
    return Fl_Button::handle(event);

  switch(event) {
    case FL_ENTER: highlight = 1; image_set(); redraw(); return 1;
    case FL_LEAVE: highlight = 0; image_set(); redraw(); return 1;
    case FL_PUSH:  highlight = 1; up = 0; image_set(); redraw(); return 1;
    case FL_RELEASE: if(highlight) {
        if(current_move.from_row) {
          if(current_move.from_row == row && current_move.from_col == col) {
            current_move.from_row = current_move.from_col = 0;
            remember = 0;
          } else {
            current_move.to_row = row;
            current_move.to_col = col;
//            current_move.dir =
//            current_move.dist =
            current_move.captured_stone_id = square[row][col].stone_id();
            current_move.apply();
//            current_board_val = board_eval();
            played_move[current_move_number] = previous_move = current_move;
            nb_of_played_moves = ++current_move_number;
            current_move.from_row = current_move.from_col = 0;
            remember = 1;
          }
          board_draw();
        } else {
          current_move.from_row = row;
          current_move.from_col = col;
          current_move.stone_id = square[row][col].stone_id();
          remember = 1;
          half_move_draw();
        }
      }
      up = 1; image_set(); redraw(); return 1;
    default:
      return Fl_Button::handle(event);
  }
}

/*
int to_int(const char *c, const int max_val=100)
{ int value = 0;

  while ((*c)>='0' && (*c)<='9') {
    value = value*10 + int(*c)-int('0');
    ++c;
  }
  if(value>=max_val) return value%max_val;
  return value;
}
*/

int Think_Button::handle(int event) {
  if(thinking || nb_of_components[0]==1 || nb_of_components[1]==1)
      return Fl_Button::handle(event);

  switch(event) {
    case FL_RELEASE:
      thinking = true;
      max_depth[player] = int(depth_input->value());
      max_time [player] = int(time_input->value());
      think();
      recommended_move.apply();
      played_move[current_move_number] = previous_move = recommended_move;
      nb_of_played_moves = ++current_move_number;
      current_move.from_row = current_move.from_col = 0;
      board_draw();
      redraw();
      Fl_Button::handle(event);
      thinking = false;
      return 1;
    default:
      return Fl_Button::handle(event);
  }
}

int Restart_Button::handle(int event) {
  if(thinking)
      return Fl_Button::handle(event);

  switch(event) {
    case FL_RELEASE:
      while(current_move_number) {
        played_move[--current_move_number].undo();
        current_move.from_row = current_move.from_col = 0;
        if(current_move_number) {
          previous_move = played_move[current_move_number-1];
        }
        else {
          previous_move.from_row = previous_move.from_col =
          previous_move.to_row = previous_move.to_col = 0;
        }
        board_draw();
        redraw();
      }
      Fl_Button::handle(event);
      return 1;
    default:
      return Fl_Button::handle(event);
  }
}

int Undo_Button::handle(int event) {
  if(thinking)
      return Fl_Button::handle(event);

  switch(event) {
    case FL_RELEASE:
      if(current_move_number) {
        played_move[--current_move_number].undo();
        current_move.from_row = current_move.from_col = 0;
        if(current_move_number) {
          previous_move = played_move[current_move_number-1];
        }
        else {
          previous_move.from_row = previous_move.from_col =
          previous_move.to_row = previous_move.to_col = 0;
        }
        board_draw();
        redraw();
      }
      Fl_Button::handle(event);
      return 1;
    default:
      return Fl_Button::handle(event);
  }
}

int Redo_Button::handle(int event) {
  if(thinking)
      return Fl_Button::handle(event);

  switch(event) {
    case FL_RELEASE:
      if(current_move_number<nb_of_played_moves) {
        previous_move = played_move[current_move_number++];
        previous_move.apply();
        current_move.from_row = current_move.from_col = 0;
        board_draw();
        redraw();
      }
      Fl_Button::handle(event);
      return 1;
    default:
      return Fl_Button::handle(event);
  }
}

int GoToEnd_Button::handle(int event) {
  if(thinking)
      return Fl_Button::handle(event);

  switch(event) {
    case FL_RELEASE:
      while(current_move_number<nb_of_played_moves) {
        previous_move = played_move[current_move_number++];
        previous_move.apply();
        current_move.from_row = current_move.from_col = 0;
        board_draw();
        redraw();
      }
      Fl_Button::handle(event);
      return 1;
    default:
      return Fl_Button::handle(event);
  }
}

void main_callback(Fl_Widget*, void*) {
  if(light) delete[] light;
//    for(int s=0; s<3; ++s) for(int a=0; a<2; ++a) for(int m=0; m<2; ++m)
//        if(square_shot[s][a][m]) delete[] square_shot[s][a][m];
  exit(0);
}

// --------------------------------------------------------------------------

Fl_Value_Input *board_size_input, *initial_setup_input;
#include <FL/Fl_Return_Button.H>

class FL_EXPORT OK_Button : public Fl_Return_Button {
public:
  OK_Button(void)
  : Fl_Return_Button(40, 70, 50, 25, "OK") {
    //this->labeltype(FL_ENGRAVED_LABEL);
  };
  int handle(int event);
};

int OK_Button::handle(int event) {
  switch(event) {
    case FL_RELEASE:
      N = int(board_size_input->value());
      INITIAL_SETUP = int(initial_setup_input->value());
      Fl_Button::handle(event);
      // delete window;
      return 1;
    default:
      return Fl_Button::handle(event);
  }
}

OK_Button *ok_button;

void setup_input(int argc, char *argv[]) {
  window = new Fl_Window (130, 100);

  board_size_input = new Fl_Value_Input(90, 10, 22, 20, "Board size ");
  board_size_input->step(1);
  board_size_input->value(8);
  board_size_input->bounds(4, 16);

  initial_setup_input = new Fl_Value_Input(90, 40, 22, 20, "Initial setup ");
  initial_setup_input->step(1);
  initial_setup_input->value(3);
  initial_setup_input->bounds(0, 8);

  ok_button = new OK_Button();

  window->end ();
  window->show (argc, argv);
  do Fl::wait();
  while(N==0);
  delete board_size_input;
  delete initial_setup_input;
  delete ok_button;
  delete window;
}

// --------------------------------------------------------------------------

int main (int argc, char *argv[])
{
    setup_input(argc, argv);
    
    window = new Fl_Window (SQUARE_WIDTH*N+250, SQUARE_WIDTH*N+50,"LoAdstone 2.0");
    window->callback(main_callback);

// --------------    
    light_new();
    square_shoot();
    light_delete();
// --------------
    board_box_new();
    board_new();
    board_setup();
// --------------
    rand_init(0);

    game_new();
    
    board_draw();

    window->end ();
    window->show (argc, argv);

    return Fl::run();
}
