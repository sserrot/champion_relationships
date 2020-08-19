---
title: "League Champion Relationships"
author: "Santiago Torres"
date: "October 21, 2016"
output: html_document
---


## Exploring The Data
### Lets take a look at the data we got in our newly created .json file.
#### Number of Champions


```r
numChampions <- nrow(champ_relations)
numChampions
```

```
## [1] 150
```

#### Column Names

```r
colnames(champ_relations)
```

```
## [1] "champion_name" "region"        "related"       "race"         
## [5] "role"
```
Read in vectors


```r
# lets try create a vector of all the champions
testVertexNames <- as.vector(champ_relations$champion_name)
head(testVertexNames)
```

```
## [[1]]
## [1] "Aatrox"
## 
## [[2]]
## [1] "Ahri"
## 
## [[3]]
## [1] "Akali"
## 
## [[4]]
## [1] "Alistar"
## 
## [[5]]
## [1] "Amumu"
## 
## [[6]]
## [1] "Anivia"
```

```r
# this weird format is due to the JSON data
# lets just iterate through the champion names to store the vertexNames
vertexNames <- c()

for (champ in champ_relations$champion_name){
  vertexNames <- c(vertexNames,tolower(champ))}
```

```r
# lets take a look at the names
head(vertexNames)
```

```
## [1] "aatrox"  "ahri"    "akali"   "alistar" "amumu"   "anivia"
```

In order to add our edges of friends, we have to iterate through it again
since JSON stores multiple friends in one pair with their respective champion, we cannot use the same iteration
Edges are also more complex because we have to store the champion with its edge

Here is the data for friends

## Creating the graph

### Vertex creation / Nodes


```r
head(champ_relations$related)
```

```
## [[1]]
## [1] "Tryndamere" "Varus"      "Kayn"      
## 
## [[2]]
## [1] "Yasuo"  "Lillia" "Wukong"
## 
## [[3]]
## [1] "Kennen" "Shen"   "Jhin"   "Zed"   
## 
## [[4]]
## [1] "Xin Zhao"
## 
## [[5]]
## [1] ""
## 
## [[6]]
## [1] "Nunu & Willump" "Ashe"           "Ornn"           "Volibear"
```

```r
# note the pair in [[2]]
# we have to create a better loop
# so we have to create an instance of the champion for each friend connection it has

#the original data 
edgeFriendsSource <- c() #empty edge for loop
edgeFriendsTarget <- c()

i <- 1
f <- 1

while(i <= numChampions) {
  #champName
  champName <- champ_relations$champion_name[[i]]
  #how many friends?
  numFriends <- length(champ_relations$related[[i]])
  while (numFriends > 0 && f <= numFriends){
    if (champ_relations$related[[i]][f] !="")
      {
      edgeFriendsSource <- c(edgeFriendsSource,tolower(champName))
      edgeFriendsTarget <- c(edgeFriendsTarget,tolower(champ_relations$related[[i]][f]))
    }
    f <- f + 1
    }
  f <- 1
  i <- i +1
}
```


```r
head(edgeFriendsSource)
```

```
## [1] "aatrox" "aatrox" "aatrox" "ahri"   "ahri"   "ahri"
```

```r
head(edgeFriendsTarget)
```

```
## [1] "tryndamere" "varus"      "kayn"       "yasuo"      "lillia"    
## [6] "wukong"
```

## Create Vertex Attributes

Lets create the attributes for the faction of champions


```r
i <- 1
f <- 1
edgeFactionSource <- c() #empty edge for loop
edgeFactionTarget <- c()
while(i <= numChampions) {
  #champName
  numFactions <- length(champ_relations$region[i])
  for (faction in champ_relations$region){
    if (f < 151) {
    if (champ_relations$region[[f]] !="" && f < 151)
    {
      champName <- champ_relations$champion_name[[f]] #133
      edgeFactionSource <- c(edgeFactionSource, tolower(champName))
      edgeFactionTarget <- c(edgeFactionTarget, champ_relations$region[[f]])
    }
    f <- f + 1
    }
  }
  i <- i+1
}
head(edgeFactionSource)
```

```
## [1] "aatrox"  "ahri"    "akali"   "alistar" "amumu"   "anivia"
```

```r
head(edgeFactionTarget)
```

```
## [1] "Runeterra" "Ionia"     "Ionia"     "Runeterra" "Shurima"   "Freljord"
```

## Creating Connections/Edges
## Graphing the data


```r
# globals
vertexSize <- 7
vLabelSize <- 1
vLabelDist <- 0
vLabelColor <- "darkblue"
vLabelFont <- 2 # bold text
vLabelDegree = -pi/2
eArrowSize <- 1
eArrowWidth<- .7
l <- layout.fruchterman.reingold
```

Graph of both


```r
dfEdge <- as.data.frame(edgeFriendsSource, stringsAsFactors=FALSE)
dfEdge["friendsTarget"] <- edgeFriendsTarget

# vertex dataframe
dfVertex <- as.data.frame(vertexNames, stringsAsFactors=FALSE)
dfVertex["ID"] <- vertexNames

both <- graph_from_data_frame(d=dfEdge, vertices = dfVertex, directed = T)
E(both)$color <- "darkgreen" # green for friends
#both <- add_edges(both, edgefriends, attr=list(color="red")) #red for enemies

both_layout <- layout.fruchterman.reingold(both, niter=10000)

plot(both, layout = both_layout)
```

<img src="LoLChampRelationships_files/figure-html/unnamed-chunk-9-1.png" width="672" />

```r
#awesome, it works
```

Here we add factions to the graph


```r
# add factions

V(both)$Faction = as.character(edgeFactionTarget[match(V(both)$name, edgeFactionSource)])
head(V(both)$Faction)
```

```
## [1] "Runeterra" "Ionia"     "Ionia"     "Runeterra" "Shurima"   "Freljord"
```

```r
allFactions = unique(V(both)$Faction)
factionColors <- c('red',NA,'lightblue','blue','brown','gold','lawngreen','orange',NA,'purple', 'black','darkgreen','darkgray','ivory','darkblue',NA,NA,NA,NA,NA)

# add a key for colors
factionNumber <- function ( faction ) {
  match( faction, allFactions )}

V(both)$color <- factionColors[factionNumber(V(both)$Faction)]
```

graph both


```r
plot(both, layout = both_layout)
```

<img src="LoLChampRelationships_files/figure-html/unnamed-chunk-11-1.png" width="672" />

This is very ugly so let's try and fix it up.


```r
V(both)$size <- vertexSize
V(both)$label.cex <- vLabelSize
V(both)$label.dist <- vLabelDist
V(both)$label.color <- vLabelColor
V(both)$label.font <- vLabelFont
V(both)$label.degree = vLabelDegree
E(both)$arrow.size <- eArrowSize
E(both)$arrow.width <- eArrowWidth

plot(both, layout=both_layout, asp = 0, frame = TRUE, main = "Champion Relationships")
```

<img src="LoLChampRelationships_files/figure-html/unnamed-chunk-12-1.png" width="672" />

Friends graph

```r
friends <- graph_from_data_frame(d=dfEdge, vertices = dfVertex, direct = T)

E(friends)$color <- "darkgreen" # green for friends
V(friends)$Faction = as.character(edgeFactionTarget[match(V(friends)$name, edgeFactionSource)])

#Factions added!

allFactions = unique(V(friends)$Faction)
factionColors <- c('red',NA,'lightblue','blue','brown','gold','lawngreen','orange',NA,'purple', 'black','darkgreen','darkgray','ivory','darkblue',NA,NA,NA,NA,NA)

V(friends)$color <- factionColors[factionNumber(V(friends)$Faction)]
V(friends)$size <- vertexSize
V(friends)$label.cex <- vLabelSize
V(friends)$label.dist <- vLabelDist
V(friends)$label.color <- vLabelColor
V(friends)$label.font <- vLabelFont
V(friends)$label.degree = vLabelDegree
E(friends)$arrow.size <- eArrowSize
E(friends)$arrow.width <- eArrowWidth

#pdf("friends.pdf",10,10) #saves graph as a pdf

plot(friends, frame = TRUE, main = "Champion Friendships")
```

<img src="LoLChampRelationships_files/figure-html/unnamed-chunk-13-1.png" width="1728" />

```r
# legend(x=-1.5, y=-1.1, c("Newspaper","Television", "Online News"), pch=21,
# 
#        col="#777777", pt.bg=colrs, pt.cex=2, cex=.8, bty="n", ncol=1)
```
## Graph Calculations

### Centrality

```r
centr_degree(friends)$centralization
```

```
## [1] 0.03189046
```

```r
centr_clo(friends, mode = "all")$centralization
```

```
## Warning in centr_clo(friends, mode = "all"): At centrality.c:2784 :closeness
## centrality is not well-defined for disconnected graphs
```

```
## [1] 0.03512951
```

```r
head(centr_betw(friends)$res)
```

```
## [1] 948.9654407 308.0287209   0.6666667  73.4301587   0.0000000 297.3935426
```

```r
centr_eigen(friends)$centralization
```

```
## [1] 0.9529647
```

#### Betweenness


```r
highest <- max(betweenness(friends))
index_of_highest <- match(highest, betweenness(friends))
print(index_of_highest)
```

```
## [1] 99
```

```r
friends[[index_of_highest]]
```

```
## $ryze
## + 7/150 vertices, named, from 51bff4d:
## [1] brand        galio        malzahar     miss fortune nasus       
## [6] sona         trundle
```

```r
#darius is the point of highest connection between all friends

highest <- max(betweenness(friends))
index_of_highest <- match(highest, betweenness(friends))
print(index_of_highest) 
```

```
## [1] 99
```

```r
friends[[index_of_highest]] 
```

```
## $ryze
## + 7/150 vertices, named, from 51bff4d:
## [1] brand        galio        malzahar     miss fortune nasus       
## [6] sona         trundle
```

```r
#garen between friends

highest <- max(betweenness(both)) 
index_of_highest <- match(highest, betweenness(both)) 
print(index_of_highest) 
```

```
## [1] 99
```

```r
both[[index_of_highest]] 
```

```
## $ryze
## + 7/150 vertices, named, from 4ef5cef:
## [1] brand        galio        malzahar     miss fortune nasus       
## [6] sona         trundle
```

```r
#garen again
```

#### Closeness Least Friends, friends, Both


```r
closest <- min(closeness(friends))
```

```
## Warning in closeness(friends): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
index_of_closest <- match(closest, closeness(friends))
```

```
## Warning in closeness(friends): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
print(index_of_closest)
```

```
## [1] 5
```

```r
friends[[index_of_closest]]
```

```
## $amumu
## + 0/150 vertices, named, from 51bff4d:
```

```r
#aurelionsol friends

closest <- min(closeness(friends))
```

```
## Warning in closeness(friends): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
index_of_closest <- match(closest, closeness(friends))
```

```
## Warning in closeness(friends): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
print(index_of_closest) 
```

```
## [1] 5
```

```r
friends[[index_of_closest]] 
```

```
## $amumu
## + 0/150 vertices, named, from 51bff4d:
```

```r
#aatrox friends

closest <- min(closeness(both)) 
```

```
## Warning in closeness(both): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
index_of_closest <- match(closest, closeness(both)) 
```

```
## Warning in closeness(both): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
print(index_of_closest) 
```

```
## [1] 5
```

```r
both[[index_of_closest]] 
```

```
## $amumu
## + 0/150 vertices, named, from 4ef5cef:
```

```r
#aurelionsol again
```

#### Closeness Most Friends, friends, Both


```r
most <- max(closeness(friends))
```

```
## Warning in closeness(friends): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
index_of_most <- match(most, closeness(friends))
```

```
## Warning in closeness(friends): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
print(index_of_most)
```

```
## [1] 29
```

```r
friends[[index_of_most]]
```

```
## $fiddlesticks
## + 2/150 vertices, named, from 51bff4d:
## [1] nocturne shaco
```

```r
#kled most friends

most <- max(closeness(friends))
```

```
## Warning in closeness(friends): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
index_of_most <- match(most, closeness(friends))
```

```
## Warning in closeness(friends): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
print(index_of_most) 
```

```
## [1] 29
```

```r
friends[[index_of_most]] 
```

```
## $fiddlesticks
## + 2/150 vertices, named, from 51bff4d:
## [1] nocturne shaco
```

```r
#ivern friends (3)

most <- max(closeness(both)) 
```

```
## Warning in closeness(both): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
index_of_most <- match(most, closeness(both)) 
```

```
## Warning in closeness(both): At centrality.c:2784 :closeness centrality is not
## well-defined for disconnected graphs
```

```r
print(index_of_most) 
```

```
## [1] 29
```

```r
both[[index_of_most]] 
```

```
## $fiddlesticks
## + 2/150 vertices, named, from 4ef5cef:
## [1] nocturne shaco
```

```r
#kled again
```


#### Eigenvector Centrality, most influential vertex


```r
influential <- max(evcent(friends)$vector)
index_of_influential <- match(influential, evcent(friends)$vector)
print(index_of_influential)
```

```
## [1] 78
```

```r
#friends[[index_of_influential]]
#kled most friends

influential <- max(evcent(friends)$vector)
index_of_influential <- match(influential, evcent(friends)$vector)
print(index_of_influential)
```

```
## [1] 78
```

```r
friends[[index_of_influential]]
```

```
## $nasus
## + 8/150 vertices, named, from 51bff4d:
## [1] azir       brand      cassiopeia renekton   ryze       sivir      taliyah   
## [8] xerath
```

```r
#ivern friends (3)

most <- max(evcent(both)$vector)
index_of_influential <- match(influential, evcent(both)$vector)
print(index_of_influential)
```

```
## [1] 78
```

```r
#both[[index_of_influential]]
#kled again
```



#### Images in Graph

```r
imgname <- list()
imgfilename <- list()
  
for (x in 1:151)
    {
    imgname = c(imgname, paste(vertexNames[x], ".png", sep =""))
    imgfilename <- c(imgfilename, file.path(path_to_files,imgname[[x]]))
    }
```


```r
set.seed(1)
# arrows point to x is friends with

l <- layout.norm(layout.fruchterman.reingold(friends, niter = 500, coolexp = .6))
```

```
## Warning in layout_with_fr(structure(list(150, TRUE, c(0, 0, 0, 1, 1, 1, :
## Argument `coolexp' is deprecated and has no effect
```

```r
V(friends)$label.cex <- .01
V(friends)$size <- .008
E(friends)$arrow.size <- 1.25
#E(friends)$arrow.width <- 1

plot(friends, layout = l, frame = TRUE, main = "Champion Relationships")

img <- lapply(imgfilename, png::readPNG)

for(i in 1:nrow(l)) {  
  rasterImage(img[[i]], l[i, 1]-0.02, l[i, 2]-0.02, l[i, 1]+0.02, l[i, 2]+0.02)
}
```

<img src="LoLChampRelationships_files/figure-html/unnamed-chunk-20-1.png" width="1728" />


```r
set.seed(1)
# arrows point to x is friends with
l <- layout.norm(layout.fruchterman.reingold(friends, niter = 500, coolexp = .6))
```

```
## Warning in layout_with_fr(structure(list(150, TRUE, c(0, 0, 0, 1, 1, 1, :
## Argument `coolexp' is deprecated and has no effect
```

```r
V(friends)$label.cex <- .01
V(friends)$size <- .008
E(friends)$arrow.size <- 1.25
E(friends)$arrow.width <- .5

plot(friends, layout = l, frame = TRUE, main = "Champion Relationships")

img <- lapply(imgfilename, png::readPNG)

for(i in 1:nrow(l)) {  
  rasterImage(img[[i]], l[i, 1]-0.02, l[i, 2]-0.02, l[i, 1]+0.02, l[i, 2]+0.02)
}
```

<img src="LoLChampRelationships_files/figure-html/unnamed-chunk-21-1.png" width="1728" />


```r
set.seed(1)
# arrows point to x is friends with

l <- layout.norm(layout.fruchterman.reingold(both, niter = 500, coolexp = .6))
```

```
## Warning in layout_with_fr(structure(list(150, TRUE, c(0, 0, 0, 1, 1, 1, :
## Argument `coolexp' is deprecated and has no effect
```

```r
V(both)$label.cex <- .01
V(both)$size <- .008
E(both)$arrow.size <- 1.25
E(both)$arrow.width <- 1

plot(both, layout = l, frame = TRUE, main = "Champion Relationships")

img <- lapply(imgfilename, png::readPNG)

for(i in 1:nrow(l)) {  
  rasterImage(img[[i]], l[i, 1]-0.02, l[i, 2]-0.02, l[i, 1]+0.02, l[i, 2]+0.02)
}
```

<img src="LoLChampRelationships_files/figure-html/unnamed-chunk-22-1.png" width="1728" />
