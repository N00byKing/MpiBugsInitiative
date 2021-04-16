/* This file is part of MUST (Marmot Umpire Scalable Tool)
 *
 * Copyright (C)
 *  2010-2016 ZIH, Technische Universitaet Dresden, Federal Republic of Germany
 *  2010-2018 Lawrence Livermore National Laboratories, United States of America
 *  2013-2018 RWTH Aachen University, Federal Republic of Germany
 *
 * See the LICENSE file in the package base directory for details
 */

/**
 * @file overlapIbcast.c
 * A must overlap test.
 * Bcast that overlaps a pending receive request
 *
 * @author Joachim Protze
 */
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include "mustTest.h"

#define COUNT 4


int main (int argc, char** argv)
{

    int fType, pack_size, position=0,i=0,j,rank,size;
    char *packbuff ;
    MPI_Init (&argc, &argv);
    MPI_Comm_rank (MPI_COMM_WORLD, &rank);
    MPI_Comm_size (MPI_COMM_WORLD, &size);

    MPI_Status status[COUNT];
    MPI_Request request[COUNT];
    //Enough tasks ?
    if (size < 2)
    {
        printf("This test needs at least 2 processes!\n");
        MPI_Finalize();
        return 1;
    }
    for (i=0; i<COUNT; i++)
    {
        request[i]=MPI_REQUEST_NULL;
    }

    MPI_Datatype        vectortype, structtype;
    
    MPI_Type_vector (10, 1, 5, MPI_INT, &vectortype);
    
    int                 blocklens[3] = {1,1,1};
    MPI_Aint            displs[3] = {0,0,4};
    MPI_Datatype        types[3] = {MPI_LB, vectortype, MPI_UB};

    MPI_Type_extent(MPI_INT, displs+2);

    int *inbuf = malloc(100000);
    MPI_Type_struct (3, blocklens, displs, types, &structtype);
    MPI_Type_commit(&structtype);

    //Say hello
    printf("Hello, I am rank %i of %i processes.\n", rank, size);;

    MPI_Ibcast(inbuf, 1, structtype, 0, MPI_COMM_WORLD, request);

    if (rank == 1)
    {
        for (i=0; i<COUNT; i++)
        {
            MPI_Send (inbuf+i, 1, structtype, 0, 42+i, MPI_COMM_WORLD);
        }
    }

    if (rank == 0)
    {
        for (i=0; i<COUNT; i++)
        {
            MPI_Recv (inbuf+i, 1, structtype, 1, 42+i, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        }
    }

//    if (rank == 0 || rank == 1)
//    {
        MPI_Waitall(COUNT,request,status);
//    }

//     MPI_Startall(COUNT,request);
    MPI_Type_free(&vectortype);
    MPI_Type_free(&structtype);
    free(inbuf);

    MPI_Finalize ();

    return 0;
}